from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from bot_runner import app as bot_app
from datetime import datetime
import os

# Global session state
call_state = {
    "start_time": None,
    "silence_events": 0,
    "user_utterances": 0,
    "unanswered_prompts": 0
}

app = FastAPI()

# Include all routes from bot_runner
app.include_router(bot_app.router)

@app.get("/")
async def home():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Phone Chatbot Server is running!",
        "endpoints": {
            "/": "Health check",
            "/start": "Start a new bot session",
            "/twilio": "Handle Twilio webhooks",
            "/end": "End call and get summary"
        }
    }

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
