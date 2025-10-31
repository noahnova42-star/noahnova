import os
from flask import Flask, request
import requests

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")  # Your bot token
CHANNEL_ID = os.getenv("CHANNEL_ID")  # e.g., -1001234567890
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# Store deep links and subscribers
video_links = {}
subscribers = set()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    # When a video is uploaded to the channel
    if "channel_post" in data and "video" in data["channel_post"]:
        video_file_id = data["channel_post"]["video"]["file_id"]
        message_id = data["channel_post"]["message_id"]

        # Create a deep link
        deep_link = f"https://t.me/{data['channel_post']['chat']['username']}?start={video_file_id}"
        video_links[video_file_id] = deep_link

        # Optionally, send the deep link back to the channel
        send_message(CHANNEL_ID, f"Deep link created: {deep_link}")

    # When user sends /start with a deep link
    if "message" in data and "text" in data["message"]:
        msg_text = data["message"]["text"]
        chat_id = data["message"]["chat"]["id"]

        if msg_text.startswith("/start "):
            file_id = msg_text.split(" ")[1]
            send_video(chat_id, file_id)
            subscribers.add(chat_id)
            send_message(chat_id, "Video forwarded! You are now subscribed for future videos.")

    return {"ok": True}

def send_message(chat_id, text):
    requests.get(f"{BASE_URL}/sendMessage", params={"chat_id": chat_id, "text": text})

def send_video(chat_id, file_id):
    requests.get(f"{BASE_URL}/sendVideo", params={"chat_id": chat_id, "video": file_id})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
