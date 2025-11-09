# bot.py
import os
import time
import secrets
import threading
import requests
from flask import Flask, request
from pymongo import MongoClient
from datetime import datetime, timezone

app = Flask(__name__)

# CONFIG (from env)
TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
MONGO_URI = os.getenv("MONGO_URI")
OWNER_ID = os.getenv("OWNER_ID")  # set to your Telegram numeric id as string
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

if not TOKEN or not BOT_USERNAME or not MONGO_URI:
    raise RuntimeError("Please set BOT_TOKEN, BOT_USERNAME and MONGO_URI environment variables.")

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
pending = db["pending_uploads"]   # temporary storage per channel
series_col = db["series"]         # saved series (persistent)

# Helpers
def tg_post(method, json_data=None, params=None):
    url = f"{BASE_URL}/{method}"
    try:
        return requests.post(url, json=json_data, params=params, timeout=30)
    except Exception as e:
        print("tg_post error:", e)
        return None

def send_message(chat_id, text):
    return tg_post("sendMessage", json_data={"chat_id": chat_id, "text": text})

def forward_message(to_chat_id, from_chat_id, message_id):
    return tg_post("forwardMessage", json_data={
        "chat_id": to_chat_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id
    })

def delete_message(chat_id, message_id):
    return requests.get(f"{BASE_URL}/deleteMessage", params={"chat_id": chat_id, "message_id": message_id}, timeout=30)

def schedule_delete(chat_id, message_id, delay_seconds=86400):
    def worker():
        time.sleep(delay_seconds)
        try:
            delete_message(chat_id, message_id)
            print(f"Deleted message {message_id} in {chat_id}")
        except Exception as e:
            print("delete_message error:", e)
    threading.Thread(target=worker, daemon=True).start()

# Utility to require owner
def is_owner(user_id):
    if OWNER_ID:
        try:
            return int(OWNER_ID) == int(user_id)
        except:
            return False
    # If OWNER_ID not set, allow (less safe)
    return True

# Incoming webhook handler
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(force=True)

    # 1) Channel posts (when bot is admin it receives channel_post updates)
    if "channel_post" in update:
        post = update["channel_post"]
        channel = post["chat"]
        channel_id = channel["id"]
        message_id = post.get("message_id")
        from_chat = post.get("sender_chat") or post.get("from")  # sometimes sender_chat for channels

        # Poster: photo/image with caption OR photo-only
        if "photo" in post and post.get("caption"):
            # Save poster as the latest poster for this channel
            pending.update_one(
                {"channel_id": channel_id},
                {"$set": {
                    "poster": {"message_id": message_id, "time": time.time()},
                    # keep existing videos if any
                }},
                upsert=True
            )
            print(f"Saved poster for channel {channel_id} message {message_id}")

        # Video/document treatment: append to pending videos
        if "video" in post or "document" in post:
            pending.update_one(
                {"channel_id": channel_id},
                {"$push": {"videos": {"message_id": message_id, "time": time.time()}}},
                upsert=True
            )
            print(f"Appended video/doc {message_id} to pending for channel {channel_id}")

    # 2) Messages (commands) — can be in channel or private
    if "message" in update:
        msg = update["message"]
        text = msg.get("text", "") or ""
        chat_id = msg["chat"]["id"]
        from_user = msg.get("from", {})
        user_id = from_user.get("id")
        is_channel = msg["chat"]["type"] in ("channel",)

        # Accept command: /create_series <title>
        if text.startswith("/create_series"):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                send_message(chat_id, "Usage: /create_series <title>\nExample: /create_series MySeriesS1")
                return {"ok": True}

            title = parts[1].strip()
            # Determine which channel to use:
            # If command issued in a channel, use that channel.
            # If issued in private, we require OWNER and must provide channel id in command optionally.
            target_channel_id = None
            if is_channel:
                target_channel_id = chat_id
            else:
                # private chat
                # Optionally support: /create_series <title> <channel_id>
                # Try to see if command includes channel id after title
                # parse title for trailing channel id in <> or raw number
                maybe = title.split()
                channel_candidate = None
                if len(maybe) > 1 and maybe[-1].lstrip("-").isdigit():
                    channel_candidate = maybe[-1]
                    title = " ".join(maybe[:-1])
                if channel_candidate:
                    try:
                        target_channel_id = int(channel_candidate)
                    except:
                        target_channel_id = None

                # if not provided, cannot proceed (we don't know which channel)
                if target_channel_id is None:
                    send_message(chat_id, "When run from private chat, include channel id after title:\n/create_series <title> <channel_id>\nOr run this command inside the channel.")
                    return {"ok": True}

            # check permission: only owner can finalize
            if not is_owner(user_id):
                send_message(chat_id, "You are not authorized to create series.")
                return {"ok": True}

            # get pending for channel
            doc = pending.find_one({"channel_id": target_channel_id})
            if not doc:
                send_message(chat_id, "No pending poster/videos found for this channel. Please upload poster + videos first.")
                return {"ok": True}

            poster = doc.get("poster")
            videos_list = doc.get("videos", [])
            if not poster and not videos_list:
                send_message(chat_id, "No poster or videos found to create series.")
                return {"ok": True}

            # Build series record
            payload = secrets.token_urlsafe(8)
            series_doc = {
                "_id": payload,
                "title": title,
                "channel_id": target_channel_id,
                "poster": poster,   # may be None
                "videos": videos_list,  # list of dicts with message_id
                "created_at": time.time(),
            }
            series_col.insert_one(series_doc)

            # Clear pending for that channel
            pending.delete_one({"channel_id": target_channel_id})

            deep_link = f"https://t.me/{BOT_USERNAME}?start={payload}"
            send_message(target_channel_id, f"✅ Series created: {title}\nDeep link:\n{deep_link}")
            # If command was run in private, also inform owner
            if not is_channel:
                send_message(chat_id, f"✅ Series created for channel {target_channel_id}: {deep_link}")

            return {"ok": True}

        # Handle /start <payload> when user clicks deep link
        if text.startswith("/start"):
            parts = text.split()
            if len(parts) < 2:
                send_message(chat_id, "Hello! Open a series deep link to receive the episodes.")
                return {"ok": True}
            payload = parts[1].strip()
            series = series_col.find_one({"_id": payload})
            if not series:
                send_message(chat_id, "❌ Invalid or expired series link.")
                return {"ok": True}

            # forward poster first
            poster = series.get("poster")
            if poster:
                resp = forward_message(chat_id, series["channel_id"], poster["message_id"])
                if resp and resp.ok:
                    mid = resp.json()["result"]["message_id"]
                    schedule_delete(chat_id, mid, delay_seconds=86400)
                time.sleep(0.5)

            # forward videos in order
            for item in series.get("videos", []):
                try:
                    resp = forward_message(chat_id, series["channel_id"], item["message_id"])
                    if resp and resp.ok:
                        mid = resp.json()["result"]["message_id"]
                        schedule_delete(chat_id, mid, delay_seconds=86400)
                    time.sleep(0.5)  # small pause to avoid rate limits
                except Exception as e:
                    print("forward error:", e)

            send_message(chat_id, f"🎬 Series delivered: {series.get('title')} (videos will auto-delete after 24h).")
            return {"ok": True}

        # Optional: admin command to list pending count
        if text.startswith("/pending_status"):
            # only owner
            if not is_owner(user_id):
                send_message(chat_id, "Not authorized.")
                return {"ok": True}
            # if running in channel, show that channel
            if is_channel:
                doc = pending.find_one({"channel_id": chat_id}) or {}
                vp = doc.get("videos", [])
                send_message(chat_id, f"Pending videos: {len(vp)}")
            else:
                # list all pending
                docs = list(pending.find({}))
                msg = "Pending uploads per channel:\n"
                for d in docs:
                    msg += f"- {d.get('channel_id')}: {len(d.get('videos',[]))} videos\n"
                send_message(chat_id, msg)
            return {"ok": True}

    return {"ok": True}

# Health
@app.route("/", methods=["GET"])
def index():
    return "Series Bot running", 200

if __name__ == "__main__":
    print("Starting bot...")
    # optional quick mongo ping
    try:
        client.admin.command("ping")
        print("✅ MongoDB connected")
    except Exception as e:
        print("❌ MongoDB connect error:", e)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
