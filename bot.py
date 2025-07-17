from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

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

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register the new command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    
    # Existing handler
    app.add_handler(CommandHandler("time", time_command))
    
    app.run_polling()
