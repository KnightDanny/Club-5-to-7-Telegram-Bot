from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

BOT_TOKEN = os.getenv("7613564885:AAFC0O4MbziGreLlKd9hJd8I1fje8eJfkzQ")  # Read from environment variable
NEXT_MEETUP = "Sunday, July 21st at 5:00 PM"

async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🎬 The next movie club meetup is on:\n📅 {NEXT_MEETUP}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("time", time_command))
    app.run_polling()
