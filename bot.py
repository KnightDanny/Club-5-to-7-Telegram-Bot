from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import os
import uvicorn
from fastapi import FastAPI
import asyncio
from telegram import __version__ as TG_VER
from telegram.constants import ParseMode

# The Bot's API token (Check in BotFather or Environment)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Variables to be set by group Admins
NEXT_MEETUP_DATE = os.getenv("INITIAL_MEETUP_DATE", "Sunday, August 9")
NEXT_MEETUP_TIME_OF_DAY = os.getenv("INITIAL_MEETUP_TIME_OF_DAY", "5:00 PM")
NEXT_MEETUP_LOCATION_DISPLAY = os.getenv("INITIAL_MEETUP_LOCATION_DISPLAY", "The Coffee Shop")
NEXT_MEETUP_LOCATION_URL = os.getenv("INITIAL_MEETUP_LOCATION_URL", "https://maps.app.goo.gl/YourCoffeeShopLocation")


ADMIN_USER_ID = os.getenv("ADMIN_USER_ID") # Telegram user ID from environment
# Check if user ID is actually Admins for the setmeetup commands
if ADMIN_USER_ID:
    try:
        ADMIN_USER_ID = int(ADMIN_USER_ID)
    except ValueError:
        print("Warning: ADMIN_USER_ID is not a valid integer. Admin features may not work.")
        ADMIN_USER_ID = None
else:
    print("Warning: ADMIN_USER_ID environment variable is not set. Admin features will be disabled.")
PORT = int(os.environ.get("PORT", 8000))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# Available commands to use in bot 
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "Hello! 👋 I'm Cleo, your Club 5 to 7 Companion.\n\n"
        "I can help you keep track of our movie club meetups.\n\n"
        "Type /help to see a list of commands you can use."
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "Here are the commands you can use with me:\n\n"
        "⏰ /meetup - See the details of the club's next meetup.\n\n"
        "❓ /help - See this list of commands again."
    )
    await update.message.reply_text(help_message)

async def meetup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location_hyperlink = f'<a href="{NEXT_MEETUP_LOCATION_URL}">{NEXT_MEETUP_LOCATION_DISPLAY}</a>'
    meetup_message = (
        "🎬 Club 5 to 7's next meetup:\n\n"
        f"📍 {location_hyperlink}\n"
        f"📅 {NEXT_MEETUP_DATE}\n"
        f"🕒 {NEXT_MEETUP_TIME_OF_DAY}\n\n"
        "We look forward to seeing you there!"
    )
    await update.message.reply_text(meetup_message, parse_mode=ParseMode.HTML)

async def setmeetup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global NEXT_MEETUP_DATE, NEXT_MEETUP_TIME_OF_DAY, NEXT_MEETUP_LOCATION_DISPLAY, NEXT_MEETUP_LOCATION_URL

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if ADMIN_USER_ID is None:
        await update.message.reply_text("Admin User ID is not configured. /setmeetup command is disabled.")
        return
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    if len(context.args) < 4:
        await update.message.reply_text(
            "Please provide the new meetup **date**, **time of day**, **location display text**, and **location URL**.\n"
            "Example:\n"
            "/setmeetup Aug 16 ; 6:00 PM ; Downtown Cinema ; https://maps.app.goo.gl/DowntownCinema\n\n"
            "Current Date: " + NEXT_MEETUP_DATE + "\n"
            "Current Time: " + NEXT_MEETUP_TIME_OF_DAY + "\n"
            "Current Location: " + NEXT_MEETUP_LOCATION_DISPLAY + "\n"
            "Current URL: " + NEXT_MEETUP_LOCATION_URL
        )
        return

    full_input = " ".join(context.args)
    parts = full_input.split(';', 3)

    if len(parts) != 4:
        await update.message.reply_text(
            "Please ensure you separate the date, time of day, location display text, and location URL with **semicolons (`;`)**.\n"
            "Example: /setmeetup Aug 16 ; 6:00 PM ; Downtown Cinema ; https://maps.app.goo.gl/DowntownCinema"
        )
        return

    new_date_str = parts[0].strip()
    new_time_of_day_str = parts[1].strip()
    new_location_display_str = parts[2].strip()
    new_location_url_str = parts[3].strip()

    # Basic validation
    if not new_date_str or len(new_date_str) > 50: 
        await update.message.reply_text("Invalid date format or too long. Please try again.")
        return
    if not new_time_of_day_str or len(new_time_of_day_str) > 50: 
        await update.message.reply_text("Invalid time of day format or too long. Please try again.")
        return
    if not new_location_display_str or len(new_location_display_str) > 100:
        await update.message.reply_text("Invalid location display text format or too long. Please try again.")
        return
    if not new_location_url_str or not (new_location_url_str.startswith("http://") or new_location_url_str.startswith("https://")):
        await update.message.reply_text("Invalid location URL. It must start with http:// or https://")
        return

    NEXT_MEETUP_DATE = new_date_str
    NEXT_MEETUP_TIME_OF_DAY = new_time_of_day_str
    NEXT_MEETUP_LOCATION_DISPLAY = new_location_display_str
    NEXT_MEETUP_LOCATION_URL = new_location_url_str

    await update.message.reply_text(
        f"✅ Movie meetup details updated!\n"
        f"Date: {NEXT_MEETUP_DATE}\n"
        f"Time: {NEXT_MEETUP_TIME_OF_DAY}\n"
        f"Location Display: {NEXT_MEETUP_LOCATION_DISPLAY}\n"
        f"Location URL: {NEXT_MEETUP_LOCATION_URL}"
    )

async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Greets new members when they join the group."""
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue

        member_name = member.first_name
        if member.last_name:
            member_name += f" {member.last_name}"

        chat_name = update.effective_chat.title if update.effective_chat.title else "this chat"

        welcome_message = (
            f"Hello, {member_name}! 👋 Welcome to {chat_name}!\n"
        )
        await update.message.reply_text(welcome_message)

# --- FastAPI Application ---
app = FastAPI()

@app.post("/webhook")
async def telegram_webhook(update: dict):
    await application.update_queue.put(Update.de_json(update, application.bot))
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Telegram bot webhook server is running."}

# --- Main execution block (now asynchronous) ---
async def run_server():
    global application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("meetup", meetup_command))
    application.add_handler(CommandHandler("setmeetup", setmeetup_command))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))

    if not WEBHOOK_URL:
        print("Error: WEBHOOK_URL environment variable is not set! Bot may not receive updates.")
    else:
        webhook_path = "/webhook"
        full_webhook_url = f"{WEBHOOK_URL}{webhook_path}"
        await application.bot.set_webhook(url=full_webhook_url)
        print(f"Webhook set to: {full_webhook_url}")

    await application.initialize()
    await application.start()

    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, lifespan="on")
    server = uvicorn.Server(config)
    await server.serve()

    await application.stop()
    await application.shutdown()

if __name__ == '__main__':
    asyncio.run(run_server())
