import os
from flask import Flask, request
import requests

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # e.g., -1001234567890
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    # Only handle messages from your channel
    if "channel_post" in update:
        post = update["channel_post"]
        if "video" in post:
            file_id = post["video"]["file_id"]
            text = f"https://t.me/{TOKEN}?start={file_id}"
            # For testing, just print or send to a user
            print("Deep link:", text)
    return {"ok": True}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
