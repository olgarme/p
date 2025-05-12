from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import logging
import sys
import traceback
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Log environment variables (without values for security)
logger.info("Checking environment variables...")
for var in ["DAILY_API_KEY", "GOOGLE_API_KEY", "DEEPGRAM_API_KEY"]:
    if os.getenv(var):
        logger.info(f"{var} is set")
    else:
        logger.error(f"{var} is not set")

# Global session state
call_state = {
    "start_time": None,
    "silence_events": 0,
    "user_utterances": 0,
    "unanswered_prompts": 0
}

app = FastAPI()

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
                "port": os.environ.get("PORT", "8000")
            }
        }
        logger.info(f"Health check response: {response}")
        return response
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/twilio")
async def handle_call(request: Request):
    """Handle incoming Twilio calls."""
    if call_state["start_time"] is None:
        call_state["start_time"] = datetime.utcnow()
        return {
            "response": "Hello! This is your AI phone assistant.",
            "pause": 5
        }

    data = await request.json()
    speech_result = data.get("SpeechResult", "").strip()
    confidence = data.get("Confidence", 0)

    if speech_result:
        call_state["user_utterances"] += 1
        call_state["unanswered_prompts"] = 0
        return {
            "response": f"You said: {speech_result}",
            "pause": 5,
            "next_prompt": "Do you want to continue?"
        }
    else:
        # No speech detected → silence
        call_state["silence_events"] += 1
        call_state["unanswered_prompts"] += 1

        if call_state["unanswered_prompts"] >= 3:
            log_summary()
            return {
                "response": "No response detected. Goodbye.",
                "end_call": True
            }

        return {
            "response": "Are you still there?",
            "pause": 5
        }

@app.post("/end")
async def end_call():
    """End the call and get a summary."""
    response = "Call ending. Goodbye."
    log_summary()
    return {
        "response": response,
        "end_call": True
    }

def log_summary():
    """Log call statistics."""
    duration = (datetime.utcnow() - call_state["start_time"]).total_seconds()
    print("\n📞 Call Summary:")
    print(f"  Duration: {duration:.2f} seconds")
    print(f"  Silence Events: {call_state['silence_events']}")
    print(f"  User Utterances: {call_state['user_utterances']}")
    print(f"  Unanswered Prompts: {call_state['unanswered_prompts']}")

    # Reset state
    for key in call_state:
        call_state[key] = 0 if isinstance(call_state[key], int) else None

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 
