import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")  # from .env file
CHANNEL_ID = os.getenv("CHANNEL_ID")  # e.g., -1001234567890
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

# ========== HELPERS ==========

def send_message(chat_id, text):
    """Send text messages via Telegram API."""
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def forward_video(chat_id, message_id):
    """Forward video from your channel to user."""
    url = f"{BASE_URL}/forwardMessage"
    payload = {"chat_id": chat_id, "from_chat_id": CHANNEL_ID, "message_id": message_id}
    requests.post(url, json=payload)

# ========== ROUTES ==========

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]

        # When the user sends /start or a deep link
        if "text" in message:
            text = message["text"]
            if text.startswith("/start"):
                parts = text.split(" ")
                if len(parts) > 1:
                    video_id = parts[1]  # deep link parameter
                    send_message(chat_id, "📦 Fetching your video...")
                    forward_video(chat_id, video_id)
                else:
                    send_message(chat_id, "👋 Send me a deep link to get a video!")

    # When you upload a video to the channel
    elif "channel_post" in update:
        post = update["channel_post"]
        if "video" in post:
            video_id = post["message_id"]
            deep_link = f"https://t.me/{os.getenv('BOT_USERNAME')}?start={video_id}"
            # Send the deep link back to your channel
            send_message(CHANNEL_ID, f"🔗 Deep link for this video:\n{deep_link}")

    return "OK", 200

# ========== WEBHOOK SETUP ==========

@app.route("/setwebhook", methods=["GET"])
def set_webhook():
    webhook_url = f"https://{os.getenv('RENDER_URL')}/{TOKEN}"
    response = requests.get(f"{BASE_URL}/setWebhook?url={webhook_url}")
    return response.json()

@app.route("/", methods=["GET"])
def home():
    return "🤖 NoahNova Bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
