from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import uvicorn
from fastapi import FastAPI
import asyncio # Make sure this is imported
from telegram import __version__ as TG_VER

# --- Configuration ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
NEXT_MEETUP = "Sunday, July 20 at 5:00 PM" # Example date from your previous code
PORT = int(os.environ.get("PORT", 8000))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

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
@app.post("/webhook")
async def telegram_webhook(update: dict):
    await application.update_queue.put(Update.de_json(update, application.bot))
    return {"status": "ok"}

# Basic health check for Render
@app.get("/")
async def root():
    return {"message": "Telegram bot webhook server is running."}

# --- Main execution block (now asynchronous) ---
async def main():
    global application # Declare application as global so it's accessible in webhook_handler

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("time", time_command))

    # --- CRITICAL FIX: AWAIT set_webhook ---
    if TG_VER.startswith('20.'):
        webhook_path = "/webhook"
        # Ensure WEBHOOK_URL is defined and not None/empty
        if not WEBHOOK_URL:
            print("Error: WEBHOOK_URL environment variable is not set!")
            return # Exit if webhook URL is not available

        # This is where the await goes
        await application.updater.bot.set_webhook(url=f"{WEBHOOK_URL}{webhook_path}")
        print(f"Webhook set to: {WEBHOOK_URL}{webhook_path}")
    else:
        print("Warning: Webhook setup might need adjustment for non-v20.x p-t-b")

    # Start the application's webhook server
    # Uvicorn will handle the incoming webhooks and pass them to application.webhook
    # application.run_webhook takes care of processing updates received by Uvicorn.
    await application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="/webhook", # This must match the path in @app.post("/webhook")
        webhook_url=f"{WEBHOOK_URL}/webhook" # This is the full URL Telegram calls
    )


if __name__ == '__main__':
    # Uvicorn needs to be run in its own process/loop, so we coordinate with asyncio
    # We will use Uvicorn's server and pass our FastAPI app to it.
    # The application.run_webhook will essentially integrate with the FastAPI app.

    # This part gets tricky because both uvicorn.run and application.run_webhook want to control the event loop.
    # The best approach for p-t-b v20 with FastAPI is to let p-t-b run its webhook server
    # and use FastAPI as the framework it runs on.

    # Re-evaluate: The previous setup with FastAPI and p-t-b run_webhook is a common pattern.
    # Let's ensure application.run_webhook is correctly hooked into FastAPI.
    # The application.run_webhook function in python-telegram-bot v20+ is designed to start
    # a web server (like a Flask/FastAPI one) and handle incoming webhooks.
    # You typically don't run uvicorn.run() *directly* if using application.run_webhook,
    # as run_webhook handles the server setup internally.

    # Let's revert to a simpler and more standard p-t-b v20 webhook setup
    # if it's causing conflicts with FastAPI's direct uvicorn.run.
    # OR we make application.run_webhook use the FastAPI app.

    # The most common pattern for p-t-b v20 webhooks with a custom web server (like FastAPI)
    # is to manually create the Bot object, set the webhook, and then pass
    # the updates received by your FastAPI app *to* the p-t-b application.
    # Your current @app.post("/webhook") does this: `await application.update_queue.put(...)`

    # Let's simplify the main block to correctly run the FastAPI app,
    # and the webhook setting needs to happen *before* the app starts serving.

    # Corrected main execution for FastAPI + PTB webhooks:
    async def run_server():
        # Build the Application and add handlers
        global application # Declare global for webhook handler
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("time", time_command))

        # Initialize the bot within the async context for webhook setup
        # Ensure the webhook URL is properly formed
        if not WEBHOOK_URL:
            print("Error: WEBHOOK_URL environment variable is not set! Bot may not receive updates.")
            # For local testing, you might use a placeholder or skip set_webhook
        else:
            webhook_path = "/webhook"
            full_webhook_url = f"{WEBHOOK_URL}{webhook_path}"
            # Await setting the webhook
            await application.bot.set_webhook(url=full_webhook_url)
            print(f"Webhook set to: {full_webhook_url}")

        # This is the key: Start the PTB application. It won't run polling here.
        # It needs to process updates that FastAPI gets.
        await application.initialize() # Initialize the application
        await application.start() # Start the application components (e.g., update queue)

        # Then, run Uvicorn. Uvicorn will manage the event loop for the web server.
        # The PTB application processes updates via `application.update_queue.put`
        # when the webhook endpoint (`@app.post("/webhook")`) is hit.
        config = uvicorn.Config(app, host="0.0.0.0", port=PORT, lifespan="on")
        server = uvicorn.Server(config)
        await server.serve()

        # Stop the application gracefully if server stops
        await application.stop()
        await application.shutdown()

    # Run the main asynchronous server setup function
    asyncio.run(run_server())
