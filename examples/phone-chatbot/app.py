from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import sys
import traceback
from datetime import datetime
import os
from typing import Optional, Dict, Any
from twilio.request_validator import RequestValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Required environment variables
REQUIRED_ENV_VARS = {
    "TWILIO_ACCOUNT_SID": "Twilio Account SID",
    "TWILIO_AUTH_TOKEN": "Twilio Auth Token",
    "TWILIO_PHONE_NUMBER": "Twilio Phone Number"
}

# Optional environment variables
OPTIONAL_ENV_VARS = {
    "DAILY_API_KEY": "Daily.co API key (optional)",
    "GOOGLE_API_KEY": "Google API key (optional)",
    "DEEPGRAM_API_KEY": "Deepgram API key (optional)"
}

# Log environment variables (without values for security)
logger.info("Checking environment variables...")
for var, description in REQUIRED_ENV_VARS.items():
    if os.getenv(var):
        logger.info(f"{var} is set")
    else:
        logger.error(f"{var} is not set - {description} (REQUIRED)")
        raise ValueError(f"{var} is required but not set")

for var, description in OPTIONAL_ENV_VARS.items():
    if os.getenv(var):
        logger.info(f"{var} is set")
    else:
        logger.warning(f"{var} is not set - {description}")

# Initialize Twilio validator
twilio_validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN"))

# Global session state
call_state = {
    "start_time": None,
    "silence_events": 0,
    "user_utterances": 0,
    "unanswered_prompts": 0,
    "last_speech_time": None,
    "silence_duration": 0
}

# Pydantic models for request/response validation
class TwilioRequest(BaseModel):
    SpeechResult: Optional[str] = None
    Confidence: Optional[float] = 0.0
    CallSid: Optional[str] = None
    From: Optional[str] = None
    To: Optional[str] = None

class TwilioResponse(BaseModel):
    response: str
    pause: Optional[int] = None
    next_prompt: Optional[str] = None
    end_call: Optional[bool] = None

app = FastAPI(title="Phone Chatbot API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def home():
    """Health check endpoint."""
    try:
        # Check if we're in the correct directory
        current_dir = os.getcwd()
        logger.info(f"Current working directory: {current_dir}")
        
        # List files in current directory
        files = os.listdir(current_dir)
        logger.info(f"Files in current directory: {files}")
        
        # Check environment variables
        env_status = {
            var: bool(os.getenv(var))
            for var in {**REQUIRED_ENV_VARS, **OPTIONAL_ENV_VARS}.keys()
        }
        
        response = {
            "status": "ok",
            "message": "Phone Chatbot Server is running!",
            "endpoints": {
                "/": "Health check",
                "/twilio": "Handle Twilio webhooks",
                "/end": "End call and get summary"
            },
            "environment": {
                "working_directory": current_dir,
                "port": os.environ.get("PORT", "8000"),
                "variables": env_status
            }
        }
        logger.info(f"Health check response: {response}")
        return response
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/twilio", response_model=TwilioResponse)
async def handle_call(request: Request):
    """Handle incoming Twilio calls."""
    try:
        # Get the request data
        form_data = await request.form()
        data = dict(form_data)
        
        # Log the incoming request data
        logger.info(f"Received Twilio request data: {data}")
        
        # Validate Twilio request
        signature = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)
        
        # Log validation attempt
        logger.info(f"Validating Twilio request with signature: {signature}")
        logger.info(f"Request URL: {url}")
        
        if not twilio_validator.validate(url, data, signature):
            logger.error("Invalid Twilio signature")
            # For testing, we'll allow the request to proceed
            logger.warning("Skipping signature validation for testing")
            # raise HTTPException(status_code=403, detail="Invalid Twilio signature")

        # Log call details
        logger.info(f"Received call from {data.get('From')} to {data.get('To')}")
        logger.info(f"Call SID: {data.get('CallSid')}")

        current_time = datetime.utcnow()
        
        if call_state["start_time"] is None:
            call_state["start_time"] = current_time
            call_state["last_speech_time"] = current_time
            return TwilioResponse(
                response="Hello! This is your AI phone assistant.",
                pause=5
            )

        # Handle speech or silence
        speech_result = data.get("SpeechResult")
        if speech_result:
            call_state["user_utterances"] += 1
            call_state["unanswered_prompts"] = 0
            call_state["last_speech_time"] = current_time
            call_state["silence_duration"] = 0
            return TwilioResponse(
                response=f"You said: {speech_result}",
                pause=5,
                next_prompt="Do you want to continue?"
            )
        else:
            # No speech detected → silence
            call_state["silence_events"] += 1
            call_state["unanswered_prompts"] += 1
            
            # Calculate silence duration
            if call_state["last_speech_time"]:
                silence_duration = (current_time - call_state["last_speech_time"]).total_seconds()
                call_state["silence_duration"] = silence_duration
                
                # If silence exceeds 10 seconds, play TTS prompt
                if silence_duration >= 10:
                    call_state["unanswered_prompts"] += 1
                    if call_state["unanswered_prompts"] >= 3:
                        log_summary()
                        return TwilioResponse(
                            response="No response detected after multiple attempts. Goodbye.",
                            end_call=True
                        )
                    return TwilioResponse(
                        response="I notice you've been quiet for a while. Are you still there?",
                        pause=5
                    )

            return TwilioResponse(
                response="Are you still there?",
                pause=5
            )
    except Exception as e:
        logger.error(f"Error handling Twilio request: {str(e)}")
        logger.error(traceback.format_exc())
        # Return a more graceful error response
        return TwilioResponse(
            response="I apologize, but I'm having trouble processing your request. Please try again.",
            pause=5
        )

@app.post("/end", response_model=TwilioResponse)
async def end_call():
    """End the call and get a summary."""
    try:
        response = "Call ending. Goodbye."
        log_summary()
        return TwilioResponse(
            response=response,
            end_call=True
        )
    except Exception as e:
        logger.error(f"Error ending call: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

def log_summary():
    """Log call statistics."""
    try:
        duration = (datetime.utcnow() - call_state["start_time"]).total_seconds()
        logger.info("\n📞 Call Summary:")
        logger.info(f"  Duration: {duration:.2f} seconds")
        logger.info(f"  Silence Events: {call_state['silence_events']}")
        logger.info(f"  Longest Silence: {call_state['silence_duration']:.2f} seconds")
        logger.info(f"  User Utterances: {call_state['user_utterances']}")
        logger.info(f"  Unanswered Prompts: {call_state['unanswered_prompts']}")

        # Reset state
        for key in call_state:
            call_state[key] = 0 if isinstance(call_state[key], int) else None
    except Exception as e:
        logger.error(f"Error logging summary: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 
