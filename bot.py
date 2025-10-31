# bot.py
import os
import json
import secrets
from flask import Flask, request
import requests

app = Flask(__name__)

# CONFIG (set these as environment variables in Render)
TOKEN = os.getenv("BOT_TOKEN")            # your bot token
BOT_USERNAME = os.getenv("BOT_USERNAME")  # your bot username without @, e.g. NoahNova_Bot
DB_FILE = "videos.json"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# Simple persistent DB for deep links
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        VIDEO_DB = json.load(f)
else:
    VIDEO_DB = {}

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(VIDEO_DB, f)

# --- Helpers ---
def send_message(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def forward_message(to_chat_id, from_chat_id, message_id):
    requests.post(f"{BASE_URL}/forwardMessage", json={
        "chat_id": to_chat_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id
    })

# --- Webhook endpoint ---
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    # 1) CHANNEL POSTS: the bot will "read" these
    if "channel_post" in update:
        post = update["channel_post"]
        channel_chat = post["chat"]  # dict with id, username (maybe)
        channel_id = channel_chat.get("id")
        username = channel_chat.get("username")
        message_id = post.get("message_id")

        # Log everything to server logs (Render logs)
        print("CHANNEL_POST from:", channel_id, username, "message_id:", message_id)
        print("Full post object:", json.dumps(post, ensure_ascii=False))

        # If it's a video or document, create a deep link (store mapping)
        if "video" in post or "document" in post:
            # we'll use message_id as identifier (you could use file_id too)
            payload = secrets.token_urlsafe(8)
            VIDEO_DB[payload] = {
                "channel_id": channel_id,
                "message_id": message_id
            }
            save_db()

            # Prepare deep link that users will open
            deep_link = f"https://t.me/{BOT_USERNAME}?start={payload}"
            # Send deep link back to the channel (optionally)
            send_message(channel_id, f"✅ Deep link created:\n{deep_link}")

        # You can add more handlers for photos, text, etc. if you want

    # 2) USER MESSAGES: handle /start <payload>
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        print("USER MESSAGE from:", chat_id, "text:", text)

        if text.startswith("/start"):
            parts = text.split()
            if len(parts) >= 2:
                payload = parts[1]
                info = VIDEO_DB.get(payload)
                if info:
                    # Forward the original message from the channel to this user
                    forward_message(chat_id, info["channel_id"], info["message_id"])
                    send_message(chat_id, "🎬 Here is the video you requested.")
                else:
                    send_message(chat_id, "❌ Link invalid or expired.")
            else:
                send_message(chat_id, "Send a link (open the deep link) to receive the video.")

    return {"ok": True}

# optional root health check
@app.route("/", methods=["GET"])
def index():
    return "Bot running", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
