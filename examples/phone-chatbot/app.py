from flask import Flask, request, jsonify
from bot_runner import BotRunner
import os

app = Flask(__name__)
bot_runner = BotRunner()

@app.route('/')
def home():
    return "Phone Chatbot Server is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    return bot_runner.handle_webhook(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000))) 

""" from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Say, Pause, Hangup
from datetime import datetime

app = Flask(__name__)

 # Global session state
call_state = {
    "start_time": None,
    "silence_events": 0,
    "user_utterances": 0,
    "unanswered_prompts": 0
}

@app.route("/twilio", methods=["POST"])
def handle_call():
    response = VoiceResponse()

    if call_state["start_time"] is None:
        call_state["start_time"] = datetime.utcnow()
        response.say("Hello! This is your AI phone assistant.")
        response.pause(length=5)  # Wait for user
        return str(response)

    speech_result = request.form.get("SpeechResult", "").strip()
    confidence = request.form.get("Confidence", 0)

    if speech_result:
        call_state["user_utterances"] += 1
        call_state["unanswered_prompts"] = 0
        response.say(f"You said: {speech_result}")
        response.pause(length=5)
        response.say("Do you want to continue?")
    else:
        # No speech detected → silence
        call_state["silence_events"] += 1
        call_state["unanswered_prompts"] += 1

        if call_state["unanswered_prompts"] >= 3:
            response.say("No response detected. Goodbye.")
            response.hangup()
            log_summary()
            return str(response)

        response.say("Are you still there?")
        response.pause(length=5)

    return str(response)

@app.route("/end", methods=["POST"])
def end_call():
    response = VoiceResponse()
    response.say("Call ending. Goodbye.")
    response.hangup()
    log_summary()
    return str(response)

def log_summary():
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
    app.run(host="0.0.0.0", port=3000) """
