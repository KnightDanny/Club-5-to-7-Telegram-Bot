from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import uvicorn
from fastapi import FastAPI
import asyncio # Keep this import
import threading

# --- Configuration (at the very top) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
NEXT_MEETUP = "Sunday, July 20 at 5:00 PM" # Using a placeholder date

# --- FastAPI App Definition (needs to be defined before any decorators like @app_web.get) ---
app_web = FastAPI()

# --- Telegram Bot Functions ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "Hello! 👋 I'm your Club 5 to 7 Telegram Bot.\n"
        "I can help you keep track of our movie club meetups.\n\n"
        "Here are the commands you can use:\n"
        "🎬 /time - Get the date and time of the next movie club meetup.\n"
        "❓ /help - See this list of commands again."
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "Here are the commands you can use with me:\n"
        "🎬 /time - Get the date and time of the next movie club meetup.\n"
        "❓ /help - See this list of commands again."
    )
    await update.message.reply_text(help_message)

async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🎬 The next movie club meetup is on:\n📅 {NEXT_MEETUP}")

# --- Dummy Web Server Endpoint for Render's Health Check ---
@app_web.get("/")
async def root():
    return {"message": "Telegram bot is running in polling mode."}

# --- Function to run the Telegram bot polling ---
def run_telegram_bot_polling():
    # *** CRITICAL FIX: Set up an event loop for this thread ***
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("time", time_command))

    # Now run the polling loop using the newly created event loop
    application.run_polling(poll_interval=1.0) # poll_interval is good for stability

# --- Main execution block ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))

    # Start the Telegram bot polling in a separate thread
    telegram_thread = threading.Thread(target=run_telegram_bot_polling)
    telegram_thread.start()

    # Run the dummy web server
    # Uvicorn itself manages its own asyncio loop in the main thread
    uvicorn.run(app_web, host="0.0.0.0", port=port)
