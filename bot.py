from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import uvicorn
from fastapi import FastAPI 
import asyncio
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Read from environment variable
# Use a more current date for the example, reflecting the current time
NEXT_MEETUP = "Saturday, August 9 at 5:00 PM" # Updated example date

# --- New: Command to start the bot and list commands ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "Hello! 👋 I'm your Club 5 to 7 Telegram Bot.\n"
        "I can help you keep track of our movie club meetups.\n\n"
        "Here are the commands you can use:\n"
        "🎬 /time - Get the date and time of the next movie club meetup.\n"
        "❓ /help - See this list of commands again."
    )
    await update.message.reply_text(welcome_message)

# --- New: Command to provide help/list commands ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "Here are the commands you can use with me:\n"
        "🎬 /time - Get the date and time of the next movie club meetup.\n"
        "❓ /help - See this list of commands again."
    )
    await update.message.reply_text(help_message)


async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🎬 The next movie club meetup is on:\n📅 {NEXT_MEETUP}")

@app_web.get("/")
async def root():
    return {"message": "Telegram bot is running in polling mode."}

# Function to run the Telegram bot polling
def run_telegram_bot_polling():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("time", time_command))
    application.run_polling(poll_interval=1.0) # Add poll_interval to prevent rapid polling if issues

if __name__ == '__main__':
    # Get the port from Render's environment variable
    port = int(os.environ.get("PORT", 8000))

    # Run the Telegram bot polling in a separate thread
    # This prevents the web server from blocking the bot, and vice versa
    telegram_thread = threading.Thread(target=run_telegram_bot_polling)
    telegram_thread.start()

    # Run the dummy web server
    uvicorn.run(app_web, host="0.0.0.0", port=port)
