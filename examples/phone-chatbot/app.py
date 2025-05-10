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