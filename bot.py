import os
from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import Application
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
BOT_USERNAME = os.getenv('BOT_USERNAME')
PORT = int(os.getenv('PORT', 8000))

# Initialize FastAPI and bot
app = FastAPI()
bot = Bot(token=BOT_TOKEN)

async def send_message(chat_id: int, text: str):
    """Send text messages to users or channel"""
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

async def forward_video(chat_id: int, message_id: int):
    """Forward videos from channel to users"""
    try:
        await bot.forward_message(
            chat_id=chat_id,
            from_chat_id=CHANNEL_ID,
            message_id=message_id
        )
        return True
    except Exception as e:
        print(f"Error forwarding video: {e}")
        return False

@app.get("/")
async def health_check():
    return {"status": "alive"}

@app.post(f"/{BOT_TOKEN}")
async def webhook_handler(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, bot)
        
        if update.channel_post and update.channel_post.video:
            message_id = update.channel_post.message_id
            deep_link = f"https://t.me/{BOT_USERNAME}?start={message_id}"
            await send_message(CHANNEL_ID, f"🎥 Share this video:\n{deep_link}")
        
        if update.message and update.message.text:
            if update.message.text.startswith('/start'):
                args = update.message.text.split()[1:]
                if args:
                    await forward_video(update.message.chat_id, int(args[0]))
                else:
                    await send_message(update.message.chat_id, "Welcome! Click a video link to receive it.")
        
        return {"ok": True}
    except Exception as e:
        print(f"Error in webhook handler: {e}")
        return {"ok": False, "error": str(e)}
