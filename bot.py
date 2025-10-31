import os
from flask import Flask, request
import requests

TOKEN = os.getenv("BOT_TOKEN")  # Your bot token
CHANNEL_ID = os.getenv("CHANNEL_ID")  # Your channel ID, e.g., -1001234567890
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

# Store video file_ids in memory (you can use a database for persistence)
video_links = {}

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()

    # 1️⃣ Handle videos uploaded to your channel
    if "channel_post" in update:
        post = update["channel_post"]
        if "video" in post:
            file_id = post["video"]["file_id"]
            video_links[file_id] = file_id  # store file_id
            print(f"Video uploaded. Deep link: https://t.me/{TOKEN}?start={file_id}")

    # 2️⃣ Handle users starting the bot with deep link
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]

        if "text" in msg and msg["text"].startswith("/start"):
            parts = msg["text"].split()
            if len(parts) == 2:
                file_id = parts[1]
                if file_id in video_links:
                    # Forward the video to the user
                    requests.post(f"{BASE_URL}/sendVideo", data={
                        "chat_id": chat_id,
                        "video": file_id
                    })

    return {"ok": True}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
