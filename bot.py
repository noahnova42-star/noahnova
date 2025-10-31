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
    data = request.get_json()
    print("Received update:", data)  # Check Render logs for incoming messages

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]
        # Reply back to user
        requests.post(f"{BASE_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": f"You said: {text}"
        })
    return "OK"

def webhook():
    data = request.get_json()

    # Check for new message in the channel
    if "channel_post" in data:
        post = data["channel_post"]
        chat_id = post["chat"]["id"]

        # Only handle videos
        if "video" in post:
            file_id = post["video"]["file_id"]
            link_id = str(uuid.uuid4())  # Generate unique link
            links_db[link_id] = file_id

            # Send deep link to channel
            deep_link = f"https://t.me/{BOT_TOKEN}?start={link_id}"
            send_message(chat_id, f"Deep link created: {deep_link}")

# Health check (optional)
@app.route('/')
def index():
    return "Bot is running!"

# For local testing
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
