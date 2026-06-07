# 🎬 Club 5 to 7 Telegram Bot

> Meet **Cleo**, the friendly companion bot that keeps a local film club organized: track the next meetup, crowdsource films and themes, and let admins run the show.

<p align="left">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white">
  <img alt="python-telegram-bot" src="https://img.shields.io/badge/python--telegram--bot-20.8-2CA5E0?logo=telegram&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-webhooks-009688?logo=fastapi&logoColor=white">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-optional-336791?logo=postgresql&logoColor=white">
</p>

---

## 📖 Overview

Organizing a film club usually means logistics scattered across group chats, where good suggestions get buried and nobody is sure where the next meetup is. **Club 5 to 7** fixes that by centralizing everything in one Telegram bot.

Any member can add film and theme ideas to a shared, persistent list and pull up the next meetup details on demand, while admins keep control over the official schedule and can prune suggestions. It runs on FastAPI webhooks for efficient, event-driven updates and supports both lightweight JSON storage and production-grade PostgreSQL.

## ✨ Features

- **📅 Meetup tracking** — members query the next meetup's date, time, location, and Google Maps link.
- **💡 Crowdsourced ideas** — anyone can suggest films and themes through a friendly, conversational prompt.
- **👀 Shared lists** — browse all films and themes the club has suggested so far.
- **🔐 Admin controls** — authorized admins set meetup details and remove suggestions.
- **👋 Auto-welcome** — greets new members when they join the group.
- **💾 Dual persistence** — toggle between local JSON (zero setup) and PostgreSQL (durable, production-ready).
- **⚡ Webhook-driven** — FastAPI serves Telegram updates via webhooks instead of polling.

## 🤖 Commands

### Member commands

| Command | Description |
| --- | --- |
| `/start` | Meet Cleo and see what the bot can do. |
| `/help` | List every available command. |
| `/meetup` | Show the next meetup's date, time, and location. |
| `/suggestfilm` | Suggest a film (the bot prompts you for the title). |
| `/suggesttheme` | Suggest a theme for the month. |
| `/filmsuggestions` | View all suggested films. |
| `/themesuggestions` | View all suggested themes. |

### Admin commands (authorized users only)

| Command | Description |
| --- | --- |
| `/setmeetup [Date] ; [Time] ; [Location] ; [URL]` | Update the next meetup details (fields separated by semicolons). |
| `/removefilm [Exact Film Title]` | Remove a film from the suggestions list. |
| `/removetheme [Exact Theme]` | Remove a theme from the suggestions list. |

> **Example:** `/setmeetup July 30 ; 6:00 PM ; Downtown Cinema ; https://maps.app.goo.gl/DowntownCinema`

## 🛠 Tech Stack

| Layer | Choice |
| --- | --- |
| Bot framework | [python-telegram-bot](https://python-telegram-bot.org/) 20.8 (async) |
| Web server | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| Storage | JSON file or PostgreSQL (via `psycopg2`) |
| Dependency management | [Poetry](https://python-poetry.org/) |

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A public HTTPS URL for webhooks (e.g. from [Render](https://render.com/), [Railway](https://railway.app/), or [ngrok](https://ngrok.com/) for local testing)
- *(Optional)* A PostgreSQL database URL for durable storage

### 1. Install dependencies

Using Poetry:

```bash
pip install poetry
poetry install
```

Or with plain pip:

```bash
pip install fastapi uvicorn "python-telegram-bot==20.8" psycopg2-binary
```

### 2. Configure environment variables

Create a `.env` file or export these in your shell:

| Variable | Required | Description |
| --- | --- | --- |
| `BOT_TOKEN` | ✅ | Your Telegram bot token from BotFather. |
| `WEBHOOK_URL` | ✅ | Public base URL where the bot is hosted (the bot appends `/webhook`). |
| `ADMIN_USER_ID` | ⚠️ | Your numeric Telegram user ID. Required to enable admin commands. |
| `STORAGE_TYPE` | ➖ | `json` (default) or `postgresql`. |
| `DATABASE_URL` | ➖ | PostgreSQL connection string. Required when `STORAGE_TYPE=postgresql`. |
| `PORT` | ➖ | Port for the web server (defaults to `8000`). |

```bash
export BOT_TOKEN="your_telegram_bot_token"
export ADMIN_USER_ID="your_telegram_user_id"
export WEBHOOK_URL="https://your-server-url.com"
export STORAGE_TYPE="json"   # or "postgresql"
```

### 3. Run the bot

```bash
python bot.py
```

On startup the bot registers its webhook, initializes storage, and starts serving Telegram updates.

## 📂 Project Structure

```
Club-5-to-7-Telegram-Bot/
├── bot.py             # Core app: config, storage layer, command handlers, FastAPI webhook server
├── pyproject.toml     # Poetry config and dependencies
├── bot_data.json      # Auto-generated in JSON mode (films, themes, meetup details)
└── README.md
```

## 🧠 Design Notes

### Dual persistence layer (JSON vs. PostgreSQL)

A `STORAGE_TYPE` switch picks the backend at runtime. **JSON** keeps local development friction-free, so anyone can clone and run instantly. **PostgreSQL** is there for production, where JSON files on ephemeral filesystems get wiped on every restart.

### Webhooks over polling

Instead of constantly asking Telegram for new messages, the bot uses FastAPI-served webhooks. They are event-driven (the bot only wakes up when there is data) and leave room to add other HTTP endpoints later, such as a web dashboard.

### Async by default

All handlers use Python's `async`/`await`, so the bot can serve multiple users concurrently while waiting on network or database calls instead of blocking.

### Conversational state machine

Commands like `/suggestfilm` don't force rigid syntax. The bot tracks lightweight state in `context.user_data` and prompts the user step by step ("Please send me the film title..."), which is far nicer to use on mobile.