# bot.py
import os
import json
import secrets
import sqlite3
import threading
import time
import requests
from flask import Flask, request

app = Flask(__name__)

# CONFIG
TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")  # e.g., NoahNova_Bot
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

# --- TELEGRAM HELPERS ---
def send_message(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def forward_message(to_chat_id, from_chat_id, message_id):
    requests.post(f"{BASE_URL}/forwardMessage", json={
        "chat_id": to_chat_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id
    })

def delete_message_later(chat_id, message_id, delay_seconds=86400):
    """Deletes message after delay (default 24 hours)."""
    def delete():
        time.sleep(delay_seconds)
        requests.get(f"{BASE_URL}/deleteMessage", params={
            "chat_id": chat_id,
            "message_id": message_id
        })
    threading.Thread(target=delete).start()

# --- WEBHOOK ---
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True)

    # Handle channel posts
    if "channel_post" in update:
        post = update["channel_post"]
        channel_id = post["chat"]["id"]
        message_id = post["message_id"]

        if "video" in post or "document" in post:
            payload = secrets.token_urlsafe(8)
            save_video(payload, channel_id, message_id)

            deep_link = f"https://t.me/{BOT_USERNAME}?start={payload}"
            send_message(channel_id, f"✅ Deep link created:\n{deep_link}")

    # Handle user messages (/start <payload>)
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if text.startswith("/start"):
            parts = text.split()
            if len(parts) >= 2:
                payload = parts[1]
                info = get_video(payload)
                if info:
                    resp = requests.post(f"{BASE_URL}/forwardMessage", json={
                        "chat_id": chat_id,
                        "from_chat_id": info["channel_id"],
                        "message_id": info["message_id"]
                    })
                    if resp.ok:
                        message_id = resp.json()["result"]["message_id"]
                        delete_message_later(chat_id, message_id)
                        send_message(chat_id, "🎬 Here’s your video! It’ll delete after 24h.")
                else:
                    send_message(chat_id, "❌ Link invalid or expired.")
            else:
                send_message(chat_id, "Hi! Send me a deep link to get your video.")
        else:
            send_message(chat_id, f"You said: {text}")

    return {"ok": True}

@app.route("/", methods=["GET"])
def index():
    return "Bot running", 200

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
