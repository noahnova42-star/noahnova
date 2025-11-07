import os
import json
import secrets
import threading
import time
import requests
from flask import Flask, request

app = Flask(__name__)

# CONFIG (set these as environment variables in Render)
TOKEN = os.getenv("BOT_TOKEN")            # your bot token
BOT_USERNAME = os.getenv("BOT_USERNAME")  # your bot username without @, e.g. NoahNova_Bot
DB_FILE = "videos.json"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# --- DATABASE SETUP ---
DB_PATH = "videos.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            payload TEXT PRIMARY KEY,
            channel_id INTEGER,
            message_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

def save_video(payload, channel_id, message_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO videos VALUES (?, ?, ?)", (payload, channel_id, message_id))
    conn.commit()
    conn.close()

def get_video(payload):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT channel_id, message_id FROM videos WHERE payload=?", (payload,))
    row = c.fetchone()
    conn.close()
    return {"channel_id": row[0], "message_id": row[1]} if row else None

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

    # 1) CHANNEL POSTS
    if "channel_post" in update:
        post = update["channel_post"]
        channel_id = post["chat"]["id"]
        username = post["chat"].get("username")
        message_id = post.get("message_id")

        print("CHANNEL_POST from:", channel_id, username, "message_id:", message_id)

        if "video" in post or "document" in post:
            payload = secrets.token_urlsafe(8)
            VIDEO_DB[payload] = {"channel_id": channel_id, "message_id": message_id}
            save_db()

            deep_link = f"https://t.me/{BOT_USERNAME}?start={payload}"
            send_message(channel_id, f"✅ Deep link created:\n{deep_link}")

    # 2) USER MESSAGES
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
