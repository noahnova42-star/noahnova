import os
import json
import secrets
import threading
import time
import requests
from flask import Flask, request
from pymongo import MongoClient

app = Flask(__name__)

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")             # Your bot token
BOT_USERNAME = os.getenv("BOT_USERNAME")   # Your bot username (no @)
MONGO_URI = os.getenv("MONGO_URI")         # Your MongoDB connection string
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# --- CONNECT TO MONGO ---
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
videos = db["videos"]

# --- Helpers ---
def send_message(chat_id, text):
    return requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def forward_message(to_chat_id, from_chat_id, message_id):
    return requests.post(f"{BASE_URL}/forwardMessage", json={
        "chat_id": to_chat_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id
    })

# --- Auto delete video after 24 hours ---
def delete_message_later(chat_id, message_id, delay_seconds=86400):  # 86400 = 24 hours
    def delete():
        time.sleep(delay_seconds)
        requests.get(f"{BASE_URL}/deleteMessage", params={
            "chat_id": chat_id,
            "message_id": message_id
        })
    threading.Thread(target=delete).start()

# --- Webhook endpoint ---
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True)

    # 1️⃣ CHANNEL POSTS
    if "channel_post" in update:
        post = update["channel_post"]
        channel_id = post["chat"]["id"]
        username = post["chat"].get("username")
        message_id = post.get("message_id")

        print("CHANNEL_POST from:", channel_id, username, "message_id:", message_id)

        if "video" in post or "document" in post:
            payload = secrets.token_urlsafe(8)
            videos.insert_one({
                "_id": payload,
                "channel_id": channel_id,
                "message_id": message_id,
                "created_at": time.time()
            })

            deep_link = f"https://t.me/{BOT_USERNAME}?start={payload}"
            send_message(channel_id, f"✅ Deep link created:\n{deep_link}")

    # 2️⃣ USER MESSAGES
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        print("USER MESSAGE from:", chat_id, "text:", text)

        if text.startswith("/start"):
            parts = text.split()
            if len(parts) >= 2:
                payload = parts[1]
                info = videos.find_one({"_id": payload})
                if info:
                    response = forward_message(chat_id, info["channel_id"], info["message_id"])
                    if response.ok:
                        message_id = response.json()["result"]["message_id"]
                        delete_message_later(chat_id, message_id)
                    send_message(chat_id, "🎬 Here is the video you requested. It will disappear in 24h.")
                else:
                    send_message(chat_id, "❌ Link invalid or expired.")
            else:
                send_message(chat_id, "Send a deep link to get the video.")

    return {"ok": True}

# --- Health check ---
@app.route("/", methods=["GET"])
def index():
    return "Bot running", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
