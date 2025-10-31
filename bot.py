import os
from flask import Flask, request
import requests

app = Flask(__name__)

# Environment variables
TOKEN = os.getenv("BOT_TOKEN")  # Your bot token from .env
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# Store user IDs who requested deep links
subscribers = set()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    # When bot receives a message in the group
    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        from_user = message.get("from", {})
        user_id = from_user.get("id")

        # Check if it's a video
        if "video" in message:
            video_file_id = message["video"]["file_id"]

            # Forward video to all subscribers
            for subscriber_id in subscribers:
                send_video(subscriber_id, video_file_id)

        # Check if user sent /start to subscribe
        if "text" in message and message["text"].startswith("/start"):
            subscribers.add(chat_id)
            send_message(chat_id, "You are now subscribed! Videos from the group will be forwarded to you.")

    return {"ok": True}

def send_message(chat_id, text):
    requests.get(f"{BASE_URL}/sendMessage", params={"chat_id": chat_id, "text": text})

def send_video(chat_id, file_id):
    requests.get(f"{BASE_URL}/sendVideo", params={"chat_id": chat_id, "video": file_id})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
