import os
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from fastapi import FastAPI, Request
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
BOT_USERNAME = os.getenv('BOT_USERNAME')
RENDER_URL = os.getenv('RENDER_URL')  # Your Render deployment URL

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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command and deep links"""
    try:
        args = context.args
        if not args:
            await update.message.reply_text("Welcome! Click a video link to receive it.")
            return

        message_id = int(args[0])
        chat_id = update.effective_chat.id
        await forward_video(chat_id, message_id)
    except Exception as e:
        print(f"Error in start command: {e}")

def generate_deep_link(message_id: int) -> str:
    """Generate deep link for video sharing"""
    return f"https://t.me/{BOT_USERNAME}?start={message_id}"

# FastAPI routes
@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "alive"}

@app.post(f"/{BOT_TOKEN}")
async def webhook_handler(request: Request):
    """Handle webhook updates from Telegram"""
    data = await request.json()
    update = Update.de_json(data, bot)
    
    # Handle channel posts
    if update.channel_post and update.channel_post.video:
        message_id = update.channel_post.message_id
        deep_link = generate_deep_link(message_id)
        await send_message(
            CHANNEL_ID,
            f"🎥 Share this video:\n{deep_link}"
        )
    
    # Handle /start commands
    if update.message and update.message.text:
        if update.message.text.startswith('/start'):
            args = update.message.text.split()[1:]
            if args:
                chat_id = update.message.chat_id
                message_id = int(args[0])
                await forward_video(chat_id, message_id)
            else:
                await send_message(
                    update.message.chat_id,
                    "Welcome! Click a video link to receive it."
                )
    
    return {"ok": True}

async def setup_webhook():
    """Set up webhook for Telegram updates"""
    webhook_url = f"{RENDER_URL}/{BOT_TOKEN}"
    await bot.set_webhook(webhook_url)
    print(f"Webhook set to {webhook_url}")

# Startup event
@app.on_event("startup")
async def startup_event():
    await setup_webhook()
