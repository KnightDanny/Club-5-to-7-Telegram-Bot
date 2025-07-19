from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import os
import uvicorn
from fastapi import FastAPI
import asyncio
from telegram import __version__ as TG_VER

# --- Configuration ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Make NEXT_MEETUP a global variable so it can be modified
NEXT_MEETUP_TIME = os.getenv("INITIAL_MEETUP_TIME", "Sunday, August 9 at 5:00 PM")
NEXT_MEETUP_LOCATION = os.getenv("INITIAL_MEETUP_LOCATION", "The Coffee Shop")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID") # Get admin user ID from environment

# Convert ADMIN_USER_ID to an integer for comparison
if ADMIN_USER_ID:
    try:
        ADMIN_USER_ID = int(ADMIN_USER_ID)
    except ValueError:
        print("Warning: ADMIN_USER_ID is not a valid integer. Admin features may not work.")
        ADMIN_USER_ID = None # Set to None if invalid
else:
    print("Warning: ADMIN_USER_ID environment variable is not set. Admin features will be disabled.")
PORT = int(os.environ.get("PORT", 8000))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# --- Telegram Bot Functions ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "Hello! 👋 I'm Cleo, your Club 5 to 7 Companion.\n"
        "I can help you keep track of our movie club meetups.\n\n"
        "Type /help to see a list of commands you can use."
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "Here are the commands you can use with me:\n\n"
        "⏰ /meetup - See the date, time, & location of the club's next meetup.\n"
        "❓ /help - See this list of commands again."
    )
    await update.message.reply_text(help_message)

async def meetup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    meetup_message = (
        "🎬 Club 5 to 7's next meetup:\n\n"
        f"📅 {NEXT_MEETUP_TIME}\n"
        f"📍 {NEXT_MEETUP_LOCATION}\n"
        "We look forward to seeing you there!"
    )
    await update.message.reply_text(meetup_message)

async def setmeetup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global NEXT_MEETUP_TIME, NEXT_MEETUP_LOCATION # Declare global to modify the variables

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id # Get chat_id for potential private reply

    # 1. Check if the user is the admin
    if ADMIN_USER_ID is None:
        # Corrected: Changed `/settime` to `/setmeetup`
        await update.message.reply_text("Admin User ID is not configured. `/setmeetup` command is disabled.")
        return
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    # 2. Check if arguments are provided correctly (expecting 2 parts: time and location)
    if len(context.args) < 2:
        await update.message.reply_text(
            "Please provide both the new meetup **time** and **location**.\n"
            "Example:\n"
            "`/setmeetup Sunday, August 16 at 6:00 PM ; Downtown Cinema`\n" # Using semicolon as separator
            "Current time: " + NEXT_MEETUP_TIME + "\n"
            "Current location: " + NEXT_MEETUP_LOCATION + ""
        )
        return

    # To make parsing easier, let's assume the admin separates time and location
    # with a specific delimiter, e.g., a semicolon ';'.
    # Join all arguments and then split by the first semicolon found.
    full_input = " ".join(context.args)
    parts = full_input.split(';', 1) # Split only on the first semicolon

    if len(parts) != 2:
        await update.message.reply_text(
            "Please ensure you separate the time and location with a **semicolon (`;`)**.\n"
            "Example: `/setmeetup Sunday, August 16 at 6:00 PM ; Downtown Cinema`"
        )
        return

    new_time_str = parts[0].strip()
    new_location_str = parts[1].strip()

    # Basic validation: Check if they are not empty and reasonable length
    if not new_time_str or len(new_time_str) > 100:
        await update.message.reply_text("Invalid time format or too long. Please try again.")
        return
    if not new_location_str or len(new_location_str) > 100: # Max length for location
        await update.message.reply_text("Invalid location format or too long. Please try again.")
        return

    NEXT_MEETUP_TIME = new_time_str
    NEXT_MEETUP_LOCATION = new_location_str

    await update.message.reply_text(
        f"✅ Movie meetup details updated!\n"
        f"Time: {NEXT_MEETUP_TIME}\n"
        f"Location: {NEXT_MEETUP_LOCATION}"
    )
    # You might also want to send a notification to the main group if needed

async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Greets new members when they join the group."""
    for member in update.message.new_chat_members:
        # Avoid welcoming the bot itself if it's added to a group
        if member.id == context.bot.id:
            continue

        # Get the first name or full name of the new member
        member_name = member.first_name
        if member.last_name:
            member_name += f" {member.last_name}"

        # Get the name of the chat/group
        chat_name = update.effective_chat.title if update.effective_chat.title else "this chat"

        # Construct the welcome message
        welcome_message = (
            f"Hello, {member_name}! 👋 Welcome to {chat_name}!\n"
            "I'm Cleo, your Club 5 to 7 companion. Use /help to see available commands."
        )

        # Reply to the message that announced the new member
        await update.message.reply_text(welcome_message)


# --- FastAPI Application ---
app = FastAPI() # Renamed to 'app' to avoid conflict if you use app_web elsewhere

# Endpoint for Telegram to send updates to
@app.post("/webhook")
async def telegram_webhook(update: dict):
    # This ensures that updates received by FastAPI are processed by the PTB application
    await application.update_queue.put(Update.de_json(update, application.bot))
    return {"status": "ok"}

# Basic health check for Render
@app.get("/")
async def root():
    return {"message": "Telegram bot webhook server is running."}

# --- Main execution block (now asynchronous) ---
async def run_server():
    # Build the Application and add handlers
    global application # Declare global for webhook handler
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("meetup", meetup_command))
    application.add_handler(CommandHandler("setmeetup", setmeetup_command))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))

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

if __name__ == '__main__':
    # Run the main asynchronous server setup function
    asyncio.run(run_server())
