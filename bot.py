from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import uvicorn
from fastapi import FastAPI
from telegram import __version__ as TG_VER # To check version for webhook handler

# --- Configuration ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
NEXT_MEETUP = "Sunday, July 20 at 5:00 PM"
PORT = int(os.environ.get("PORT", 8000)) # Get port from Render
# IMPORTANT: Replace YOUR_RENDER_SERVICE_URL with your actual Render service URL
# It will look something like https://your-service-name.onrender.com
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") # This will be set on Render

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

# --- FastAPI Application ---
app = FastAPI() # Renamed to 'app' to avoid conflict if you use app_web elsewhere

# Endpoint for Telegram to send updates to
@app.post("/webhook") # This is the path Telegram will send updates to
async def telegram_webhook(update: dict):
    # Process the update from Telegram
    await application.update_queue.put(Update.de_json(update, application.bot))
    return {"status": "ok"}

# Basic health check for Render
@app.get("/")
async def root():
    return {"message": "Telegram bot webhook server is running."}

# --- Main execution block ---
if __name__ == '__main__':
    # Build the Application and add handlers
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("time", time_command))

    # Set up webhook (important step!)
    # Check if the Telegram Bot API version is 20.8+ as the method changed slightly
    if TG_VER.startswith('20.'): # For python-telegram-bot v20.x
        webhook_path = "/webhook" # Match the @app.post("/webhook") path
        application.updater.bot.set_webhook(url=f"{WEBHOOK_URL}{webhook_path}")
        print(f"Webhook set to: {WEBHOOK_URL}{webhook_path}")
    else:
        # Fallback for older versions or if webhook method changes again
        # Consider checking python-telegram-bot docs for your exact version if not 20.x
        print("Warning: Webhook setup might need adjustment for non-v20.x p-t-b")


    # Run the FastAPI server which will handle webhooks
    # Use an external FastAPI worker to manage the lifespan and webhook processing
    uvicorn.run(app, host="0.0.0.0", port=PORT, lifespan="on") # lifespan="on" is important for FastAPI apps with async initialization
