Club 5 to 7 Telegram Bot

Video Demo:  <INSERT YOUR YOUTUBE VIDEO URL HERE>

Description:

The Club 5 to 7 Bot is a comprehensive management tool designed for a local film club. It serves as an interactive assistant to help members stay organized, crowdsource movie ideas, and manage monthly meetups.

The project solves a specific community problem: organizing film club logistics usually happens in scattered text messages where suggestions get lost. This bot centralizes the schedule and democratizes the selection process by allowing any user to add suggestions to a persistent list, while giving administrators control over the final event details.

Features

Event Tracking: Users can query the bot for the next meetup location, time, and Google Maps link.

Crowdsourcing: Members can suggest films and themes.

Persistence: Supports both local JSON storage (for simplicity) and PostgreSQL (for production reliability).

Admin Tools: Authorized admins can remove suggestions and update event details via commands.

Webhook Integration: Built using FastAPI to handle Telegram updates efficiently via webhooks rather than polling.

Project Structure and Files

bot.py: This is the core application file. It contains:

Configuration: Loads environment variables for security (Tokens, IDs).

Database Logic: Functions to switch between JSON and PostgreSQL storage dynamically.

Handlers: Async functions that process Telegram commands (/start, /suggestfilm, etc.).

FastAPI App: A web server instance that listens for incoming webhooks from Telegram.

pyproject.toml: Configuration for Poetry, a modern dependency manager for Python. It lists all required libraries (python-telegram-bot, fastapi, psycopg2, etc.).

bot_data.json: (Auto-generated) If the bot is run in JSON mode, this file is created automatically to store film suggestions and meetup details locally.

Design Choices

1. Dual Persistence Layer (JSON vs. PostgreSQL)

One of the biggest design decisions was implementing a "toggleable" storage system.

Why JSON? For local development and testing, setting up a database server is overkill. I wanted the bot to be runnable immediately by anyone cloning the repo.

Why PostgreSQL? For the final deployment (e.g., on Render or Heroku), JSON files on ephemeral filesystems get deleted when the server restarts. I implemented PostgreSQL integration using psycopg2 to ensure data persists in a production environment. The code checks the STORAGE_TYPE environment variable to decide which backend to use.

2. FastAPI & Webhooks vs. Polling

While many simple bots use "polling" (constantly asking Telegram "do you have new messages?"), I chose to use Webhooks served via FastAPI.

Efficiency: Webhooks are event-driven. The bot only wakes up when it receives data, which is more efficient for server resources.

Scalability: Using FastAPI allows the bot to potentially serve other HTTP endpoints in the future (e.g., a simple web dashboard to view suggestions).

3. Asynchronous Programming

Since the bot relies on network requests (Telegram API) and database operations, I utilized Python's async and await syntax. This ensures that while the bot is waiting for a database query to finish or a message to send, it doesn't freeze; it can continue processing requests from other users concurrently.

4. State Management

For commands like /suggestfilm, I implemented a simple state machine using context.user_data. Instead of forcing users to type complex commands like /suggestfilm The Matrix, the bot prompts them conversationally ("Please send me the film title..."). This improves the user experience significantly on mobile devices.

Installation and Usage

Prerequisites:

Python 3.10+

A Telegram Bot Token (from BotFather)

(Optional) A PostgreSQL database URL

Setup:

Install dependencies:

pip install poetry
poetry install
# OR
pip install fastapi uvicorn python-telegram-bot psycopg2-binary


Set Environment Variables (create a .env file or export them):

export BOT_TOKEN="your_telegram_bot_token"
export ADMIN_USER_ID="your_telegram_user_id"
export WEBHOOK_URL="[https://your-server-url.com](https://your-server-url.com)"
export STORAGE_TYPE="json"  # or "postgresql"


Run the bot:

python bot.py
