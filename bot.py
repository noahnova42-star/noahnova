from flask import Flask, request
import requests
import uuid

# ===== CONFIG =====
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Your bot token
CHANNEL_ID = "@YourChannelUsername"  # Or -1001234567890
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
links_db = {}  # Store deep links and their corresponding file_id
# =================

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
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

    # Handle user starting bot with deep link
    elif "message" in data:
        message = data["message"]
        text = message.get("text", "")
        chat_id = message["chat"]["id"]

        if text.startswith("/start"):
            link_id = text.split(" ")[1] if len(text.split(" ")) > 1 else None
            if link_id and link_id in links_db:
                file_id = links_db[link_id]
                forward_video(chat_id, file_id)
            else:
                send_message(chat_id, "Invalid or expired link.")

    return {"ok": True}

def send_message(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def forward_video(chat_id, file_id):
    requests.post(f"{BASE_URL}/sendVideo", json={"chat_id": chat_id, "video": file_id})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
