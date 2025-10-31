from flask import Flask, request
import requests

# ====== CONFIG ======
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your bot token
CHANNEL_ID = "YOUR_CHANNEL_ID_HERE"  # Replace with your channel/chat ID, e.g., -1001234567890
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
# ====================

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text:
            reply = f"You said: {text}"
            send_message(chat_id, reply)

    return {"ok": True}

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
