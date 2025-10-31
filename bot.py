# bot.py
from flask import Flask, request
import os
import requests

app = Flask(__name__)

# Load token and channel from environment variables
TOKEN = os.getenv("BOT_TOKEN")          # Put your bot token in .env
CHANNEL_ID = os.getenv("CHANNEL_ID")    # Put your chat/channel ID in .env
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# Webhook endpoint (Telegram will send updates here)
@app.route('/webhook', methods=['POST'])
def webhook():
    return "OK"

def webhook():
            send_message(chat_id, f"Deep link created: {deep_link}")

# Health check (optional)
@app.route('/')
def index():
    return "Bot is running!"

# For local testing
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
