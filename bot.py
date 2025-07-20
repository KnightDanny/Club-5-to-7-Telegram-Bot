import json
import os
import uvicorn
from fastapi import FastAPI
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

# --- Configuration and Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
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

# --- Persistence Type Configuration ---
# Set STORAGE_TYPE to 'json' or 'postgresql'
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "json").lower() # Default to json if not set

# JSON Specific Configuration
JSON_DATA_FILE = "bot_data.json"

# PostgreSQL Specific Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if STORAGE_TYPE == "postgresql" and not DATABASE_URL:
    print("WARNING: STORAGE_TYPE is 'postgresql' but DATABASE_URL is not set. Persistence will fail.")

# Default values for meetup details
DEFAULT_MEETUP_DATE = "Sunday, July 28" # Updated default date
DEFAULT_MEETUP_TIME_OF_DAY = "5:00 PM"
DEFAULT_MEETUP_LOCATION_DISPLAY = "The Coffee Shop"
DEFAULT_MEETUP_LOCATION_URL = "https://maps.app.goo.gl/YourCoffeeShopLocation"

# --- Global Variables (to be populated from chosen storage) ---
NEXT_MEETUP_DATE = DEFAULT_MEETUP_DATE
NEXT_MEETUP_TIME_OF_DAY = DEFAULT_MEETUP_TIME_OF_DAY
NEXT_MEETUP_LOCATION_DISPLAY = DEFAULT_MEETUP_LOCATION_DISPLAY
NEXT_MEETUP_LOCATION_URL = DEFAULT_MEETUP_LOCATION_URL
FILM_SUGGESTIONS = []
THEME_SUGGESTIONS = []

# --- Database Imports and Functions (if PostgreSQL is enabled) ---
if STORAGE_TYPE == "postgresql":
    try:
        import psycopg2
        from psycopg2 import sql # sql is imported but not explicitly used in provided snippets, kept for potential future use
    except ImportError:
        print("Error: psycopg2-binary not installed. Please install it with 'pip install psycopg2-binary' if you use PostgreSQL storage.")
        psycopg2 = None # Mark as unavailable
else:
    psycopg2 = None # Ensure it's not accidentally used

def get_db_connection():
    if not psycopg2 or not DATABASE_URL:
        return None
    try:
        # Use sslmode='require' for Render PostgreSQL connections
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def initialize_db():
    if not psycopg2 or not DATABASE_URL:
        print("Skipping DB initialization: psycopg2 or DATABASE_URL not available.")
        return

    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # Create meetup_details table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS meetup_details (
                        id SERIAL PRIMARY KEY,
                        meetup_date TEXT NOT NULL,
                        meetup_time_of_day TEXT NOT NULL,
                        location_display TEXT NOT NULL,
                        location_url TEXT NOT NULL
                    );
                """)
                # Create film_suggestions table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS film_suggestions (
                        id SERIAL PRIMARY KEY,
                        title TEXT UNIQUE NOT NULL
                    );
                """)
                # Create theme_suggestions table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS theme_suggestions (
                        id SERIAL PRIMARY KEY,
                        theme TEXT UNIQUE NOT NULL
                    );
                """)
                conn.commit()
            print("Database tables initialized/checked.")
        except Exception as e:
            print(f"Error during DB initialization: {e}")
        finally:
            conn.close()
    else:
        print("Could not initialize database tables: No DB connection.")

# --- Persistence Functions for JSON ---
def load_data_json():
    global NEXT_MEETUP_DATE, NEXT_MEETUP_TIME_OF_DAY, NEXT_MEETUP_LOCATION_DISPLAY, NEXT_MEETUP_LOCATION_URL, FILM_SUGGESTIONS, THEME_SUGGESTIONS
    if os.path.exists(JSON_DATA_FILE):
        try:
            with open(JSON_DATA_FILE, "r") as f:
                data = json.load(f)
                NEXT_MEETUP_DATE = data.get("next_meetup_date", DEFAULT_MEETUP_DATE)
                NEXT_MEETUP_TIME_OF_DAY = data.get("next_meetup_time_of_day", DEFAULT_MEETUP_TIME_OF_DAY)
                NEXT_MEETUP_LOCATION_DISPLAY = data.get("next_meetup_location_display", DEFAULT_MEETUP_LOCATION_DISPLAY)
                NEXT_MEETUP_LOCATION_URL = data.get("next_meetup_location_url", DEFAULT_MEETUP_LOCATION_URL)
                FILM_SUGGESTIONS = data.get("film_suggestions", [])
                THEME_SUGGESTIONS = data.get("theme_suggestions", [])
            print("Data loaded from JSON successfully.")
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {JSON_DATA_FILE}. Starting with default data and re-saving.")
            # Attempt to reset and save valid default data
            reset_to_defaults()
            save_data_json()
        except Exception as e:
            print(f"An unexpected error occurred while loading JSON data: {e}. Starting with default data and re-saving.")
            reset_to_defaults()
            save_data_json()
    else:
        print(f"{JSON_DATA_FILE} not found. Starting with default data and creating file.")
        reset_to_defaults()
        save_data_json() # Create the file with initial defaults

def save_data_json():
    data = {
        "next_meetup_date": NEXT_MEETUP_DATE,
        "next_meetup_time_of_day": NEXT_MEETUP_TIME_OF_DAY,
        "next_meetup_location_display": NEXT_MEETUP_LOCATION_DISPLAY,
        "next_meetup_location_url": NEXT_MEETUP_LOCATION_URL,
        "film_suggestions": FILM_SUGGESTIONS,
        "theme_suggestions": THEME_SUGGESTIONS,
    }
    try:
        with open(JSON_DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
        print("Data saved to JSON successfully.")
    except Exception as e:
        print(f"Error saving data to JSON: {e}")

# --- Persistence Functions for PostgreSQL ---
def load_data_db():
    global NEXT_MEETUP_DATE, NEXT_MEETUP_TIME_OF_DAY, NEXT_MEETUP_LOCATION_DISPLAY, NEXT_MEETUP_LOCATION_URL, FILM_SUGGESTIONS, THEME_SUGGESTIONS
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # Load meetup details
                cur.execute("SELECT meetup_date, meetup_time_of_day, location_display, location_url FROM meetup_details ORDER BY id DESC LIMIT 1;")
                meetup_record = cur.fetchone()
                if meetup_record:
                    NEXT_MEETUP_DATE, NEXT_MEETUP_TIME_OF_DAY, NEXT_MEETUP_LOCATION_DISPLAY, NEXT_MEETUP_LOCATION_URL = meetup_record
                else:
                    print("No meetup details found in DB, using defaults and inserting them.")
                    # Insert defaults if table is empty
                    cur.execute(
                        "INSERT INTO meetup_details (meetup_date, meetup_time_of_day, location_display, location_url) VALUES (%s, %s, %s, %s);",
                        (DEFAULT_MEETUP_DATE, DEFAULT_MEETUP_TIME_OF_DAY, DEFAULT_MEETUP_LOCATION_DISPLAY, DEFAULT_MEETUP_LOCATION_URL)
                    )
                    conn.commit()
                    # Re-assign to globals from defaults
                    NEXT_MEETUP_DATE = DEFAULT_MEETUP_DATE
                    NEXT_MEETUP_TIME_OF_DAY = DEFAULT_MEETUP_TIME_OF_DAY
                    NEXT_MEETUP_LOCATION_DISPLAY = DEFAULT_MEETUP_LOCATION_DISPLAY
                    NEXT_MEETUP_LOCATION_URL = DEFAULT_MEETUP_LOCATION_URL


                # Load film suggestions
                cur.execute("SELECT title FROM film_suggestions;")
                FILM_SUGGESTIONS.clear() # Clear existing to avoid duplicates on reload
                FILM_SUGGESTIONS.extend([row[0] for row in cur.fetchall()])

                # Load theme suggestions
                cur.execute("SELECT theme FROM theme_suggestions;")
                THEME_SUGGESTIONS.clear() # Clear existing to avoid duplicates on reload
                THEME_SUGGESTIONS.extend([row[0] for row in cur.fetchall()])
            print("Data loaded from database successfully.")
        except Exception as e:
            print(f"Error loading data from database: {e}. Resetting to defaults.")
            reset_to_defaults()
        finally:
            conn.close()
    else:
        print("Could not load data from database: No DB connection. Using defaults.")
        reset_to_defaults()


def save_meetup_to_db():
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # Clear existing meetup details and insert the new one
                cur.execute("DELETE FROM meetup_details;")
                cur.execute(
                    "INSERT INTO meetup_details (meetup_date, meetup_time_of_day, location_display, location_url) VALUES (%s, %s, %s, %s);",
                    (NEXT_MEETUP_DATE, NEXT_MEETUP_TIME_OF_DAY, NEXT_MEETUP_LOCATION_DISPLAY, NEXT_MEETUP_LOCATION_URL)
                )
                conn.commit()
            print("Meetup details saved to database.")
        except Exception as e:
            print(f"Error saving meetup details to DB: {e}")
        finally:
            conn.close()
    else:
        print("Could not save meetup details to database: No DB connection.")

def add_film_suggestion_to_db(title):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # Use ON CONFLICT DO NOTHING to handle unique constraint without error
                cur.execute("INSERT INTO film_suggestions (title) VALUES (%s) ON CONFLICT (title) DO NOTHING;", (title,))
                conn.commit()
            print(f"Film suggestion '{title}' added/checked in DB.")
        except Exception as e:
            print(f"Error adding film suggestion to DB: {e}")
        finally:
            conn.close()
    else:
        print("Could not add film suggestion to database: No DB connection.")

def add_theme_suggestion_to_db(theme):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO theme_suggestions (theme) VALUES (%s) ON CONFLICT (theme) DO NOTHING;", (theme,))
                conn.commit()
            print(f"Theme suggestion '{theme}' added/checked in DB.")
        except Exception as e:
            print(f"Error adding theme suggestion to DB: {e}")
        finally:
            conn.close()
    else:
        print("Could not add theme suggestion to database: No DB connection.")

# --- NEW: Removal functions for PostgreSQL ---
def remove_film_from_db(title):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM film_suggestions WHERE title = %s;", (title,))
                rows_deleted = cur.rowcount
                conn.commit()
                return rows_deleted > 0 # Return True if at least one row was deleted
        except Exception as e:
            print(f"Error removing film suggestion from DB: {e}")
            return False
        finally:
            conn.close()
    print("Could not remove film suggestion from database: No DB connection.")
    return False

def remove_theme_from_db(theme):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM theme_suggestions WHERE theme = %s;", (theme,))
                rows_deleted = cur.rowcount
                conn.commit()
                return rows_deleted > 0 # Return True if at least one row was deleted
        except Exception as e:
            print(f"Error removing theme suggestion from DB: {e}")
            return False
        finally:
            conn.close()
    print("Could not remove theme suggestion from database: No DB connection.")
    return False

# --- Global Load/Save/Modify Functions (calls appropriate backend) ---
def reset_to_defaults():
    global NEXT_MEETUP_DATE, NEXT_MEETUP_TIME_OF_DAY, NEXT_MEETUP_LOCATION_DISPLAY, NEXT_MEETUP_LOCATION_URL, FILM_SUGGESTIONS, THEME_SUGGESTIONS
    NEXT_MEETUP_DATE = DEFAULT_MEETUP_DATE
    NEXT_MEETUP_TIME_OF_DAY = DEFAULT_MEETUP_TIME_OF_DAY
    NEXT_MEETUP_LOCATION_DISPLAY = DEFAULT_MEETUP_LOCATION_DISPLAY
    NEXT_MEETUP_LOCATION_URL = DEFAULT_MEETUP_LOCATION_URL
    FILM_SUGGESTIONS = []
    THEME_SUGGESTIONS = []
    print("Global data variables reset to default values.")

def load_all_data():
    print(f"Attempting to load data using {STORAGE_TYPE} storage...")
    if STORAGE_TYPE == "json":
        load_data_json()
    elif STORAGE_TYPE == "postgresql":
        load_data_db()
    else:
        print(f"Invalid STORAGE_TYPE '{STORAGE_TYPE}'. No data loaded. Using defaults.")
        reset_to_defaults()

def save_all_data_for_meetup():
    print(f"Attempting to save meetup data using {STORAGE_TYPE} storage...")
    if STORAGE_TYPE == "json":
        save_data_json() # JSON saves all data together
    elif STORAGE_TYPE == "postgresql":
        save_meetup_to_db() # DB saves meetup separately
    else:
        print(f"Invalid STORAGE_TYPE '{STORAGE_TYPE}'. Meetup data not saved.")

def add_film_suggestion_and_save(title):
    global FILM_SUGGESTIONS
    if STORAGE_TYPE == "json":
        FILM_SUGGESTIONS.append(title)
        save_data_json()
    elif STORAGE_TYPE == "postgresql":
        add_film_suggestion_to_db(title)
        load_all_data() # Reload to update global list from DB after addition
    else:
        print(f"Invalid STORAGE_TYPE '{STORAGE_TYPE}'. Film suggestion not saved.")

def add_theme_suggestion_and_save(theme):
    global THEME_SUGGESTIONS
    if STORAGE_TYPE == "json":
        THEME_SUGGESTIONS.append(theme)
        save_data_json()
    elif STORAGE_TYPE == "postgresql":
        add_theme_suggestion_to_db(theme)
        load_all_data() # Reload to update global list from DB after addition
    else:
        print(f"Invalid STORAGE_TYPE '{STORAGE_TYPE}'. Theme suggestion not saved.")

# --- NEW: Removal wrappers ---
def remove_film_suggestion_and_save(title):
    global FILM_SUGGESTIONS
    removed = False
    if STORAGE_TYPE == "json":
        if title in FILM_SUGGESTIONS:
            FILM_SUGGESTIONS.remove(title)
            save_data_json()
            removed = True
    elif STORAGE_TYPE == "postgresql":
        removed = remove_film_from_db(title)
        if removed: # Only reload if something was actually removed from DB
            load_all_data() # Reload to update global list from DB
    else:
        print(f"Invalid STORAGE_TYPE '{STORAGE_TYPE}'. Film suggestion not removed.")
    return removed

def remove_theme_suggestion_and_save(theme):
    global THEME_SUGGESTIONS
    removed = False
    if STORAGE_TYPE == "json":
        if theme in THEME_SUGGESTIONS:
            THEME_SUGGESTIONS.remove(theme)
            save_data_json()
            removed = True
    elif STORAGE_TYPE == "postgresql":
        removed = remove_theme_from_db(theme)
        if removed: # Only reload if something was actually removed from DB
            load_all_data() # Reload to update global list from DB
    else:
        print(f"Invalid STORAGE_TYPE '{STORAGE_TYPE}'. Theme suggestion not removed.")
    return removed


# --- Telegram Bot Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        welcome_message = (
            "🎉 Greetings, fellow cinephile!🎉\n"
            "I'm Cleo, your dedicated Club 5 to 7 Companion!\n\n"
            "I'm here to help our movie club stay organized and vibrant. Think of me as your personal assistant for all things related to our film discussions and meetups. \n\n"
            "Here's what I can do for you:\n\n"
            "📅 Stay Updated: Get the latest details on our next club meetup\n\n"
            "💡 Share Your Ideas: Have a brilliant film in mind that the club must watch? Or perhaps a fascinating theme you'd love to explore? Send them my way!\n\n"
            "👀 Discover Suggestions: Curious what other members are thinking? You can easily view all the films and themes that have been suggested so far.\n\n"
            "Ready to dive into the world of cinema with Club 5 to 7? Just type /help to see a full list of commands and let's get started!"
        )
        await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        help_message = (
            "Here are the commands you can use with me:\n\n"
            "⏰ /meetup - See the details of the club's next meetup.\n\n"
            "🎬 /suggestfilm [Film Title] - Suggest a film for the club to watch.\n"
            "💡 /suggesttheme [Theme Suggestion] - Suggest a theme for the month.\n\n"
            "🎥 /suggestionsfilm - See the list of suggested films.\n"
            "🎨 /suggestionstheme - See the list of suggested themes.\n\n"
            "❓ /help - See this list of commands again."
        )
        await update.message.reply_text(help_message)

async def meetup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        # Ensure latest data is loaded before displaying
        load_all_data()
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

    if not update.message:
        return

    user_id = update.effective_user.id
    # chat_id = update.effective_chat.id # Not used in this function

    if ADMIN_USER_ID is None:
        await update.message.reply_text("Admin User ID is not configured. /setmeetup command is disabled.")
        return
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    if len(context.args) < 4:
        # Ensure latest data is loaded before showing current values
        load_all_data()
        await update.message.reply_text(
            "Please provide the new meetup **date**, **time of day**, **location display text**, and **location URL**.\n"
            "Example:\n"
            "/setmeetup July 30 ; 6:00 PM ; Downtown Cinema ; https://maps.app.goo.gl/DowntownCinema\n\n\n"
            f"Current Date: {NEXT_MEETUP_DATE}\n"
            f"Current Time: {NEXT_MEETUP_TIME_OF_DAY}\n"
            f"Current Location: {NEXT_MEETUP_LOCATION_DISPLAY}\n"
            f"Current URL: {NEXT_MEETUP_LOCATION_URL}"
        )
        return

    full_input = " ".join(context.args)
    parts = full_input.split(';', 3)

    if len(parts) != 4:
        await update.message.reply_text(
            "Please ensure you separate the date, time of day, location display text, and location URL with **semicolons (;)**.\n"
            "Example: /setmeetup July 30 ; 6:00 PM ; Downtown Cinema ; https://maps.app.goo.gl/DowntownCinema"
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

    save_all_data_for_meetup() # Save meetup details to chosen storage

    await update.message.reply_text(
        f"✅ Club meetup details updated!\n"
        f"Date: {NEXT_MEETUP_DATE}\n"
        f"Time: {NEXT_MEETUP_TIME_OF_DAY}\n"
        f"Location Display: {NEXT_MEETUP_LOCATION_DISPLAY}\n"
        f"Location URL: {NEXT_MEETUP_LOCATION_URL}"
    )

async def suggest_film(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not context.args:
        await update.message.reply_text(
            "Please provide the film title you want to suggest. Example:\n"
            "/suggestfilm The Matrix"
        )
        return

    movie_title = " ".join(context.args).strip()

    if not movie_title:
        await update.message.reply_text("Film title cannot be empty.")
        return
    if len(movie_title) > 200:
        await update.message.reply_text("Film title is too long. Please shorten it.")
        return

    # Always load data to ensure FILM_SUGGESTIONS is current before checking/adding
    load_all_data()

    if movie_title not in FILM_SUGGESTIONS:
        add_film_suggestion_and_save(movie_title)
        await update.message.reply_text(f"🎬 Thank you! '{movie_title}' has been added to the film suggestions list.")
    else:
        await update.message.reply_text(f"'{movie_title}' is already in the film suggestions list. Thanks for reminding!")

async def suggest_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not context.args:
        await update.message.reply_text(
            "Please provide the theme you want to suggest. Example:\n"
            "/suggesttheme Sci-Fi Classics"
        )
        return

    theme_suggestion = " ".join(context.args).strip()

    if not theme_suggestion:
        await update.message.reply_text("Theme suggestion cannot be empty.")
        return
    if len(theme_suggestion) > 200:
        await update.message.reply_text("Theme suggestion is too long. Please shorten it.")
        return

    # Always load data to ensure THEME_SUGGESTIONS is current before checking/adding
    load_all_data()

    if theme_suggestion not in THEME_SUGGESTIONS:
        add_theme_suggestion_and_save(theme_suggestion)
        await update.message.reply_text(f"💡 Thank you! '{theme_suggestion}' has been added to the theme suggestions list.")
    else:
        await update.message.reply_text(f"'{theme_suggestion}' is already in the theme suggestions list. Thanks for reminding!")

async def show_film_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    # Always reload from storage to get the latest list
    load_all_data()

    if not FILM_SUGGESTIONS:
        await update.message.reply_text("💡 No film suggestions yet! Be the first to add one with /suggestfilm [Film Title]")
        return

    suggestions_list = "\n".join([f"{i+1}. {movie}" for i, movie in enumerate(FILM_SUGGESTIONS)])
    await update.message.reply_text(
        "🎬 Current Film Suggestions:\n"
        f"{suggestions_list}\n\n"
    )

async def show_theme_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    # Always reload from storage to get the latest list
    load_all_data()

    if not THEME_SUGGESTIONS:
        await update.message.reply_text("💡 No theme suggestions yet! Be the first to add one with /suggesttheme [Theme Suggestion]")
        return

    suggestions_list = "\n".join([f"{i+1}. {theme}" for i, theme in enumerate(THEME_SUGGESTIONS)])
    await update.message.reply_text(
        "🎨 Current Theme Suggestions:\n"
        f"{suggestions_list}\n\n"
    )

# --- NEW Admin Removal Commands ---
async def remove_film(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = update.effective_user.id

    if ADMIN_USER_ID is None:
        await update.message.reply_text("Admin User ID is not configured. /removefilm command is disabled.")
        return
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text(
            "Please provide the exact film title to remove. Example:\n"
            "/removefilm The Matrix"
        )
        return

    movie_title = " ".join(context.args).strip()

    load_all_data() # Ensure global list is up-to-date for checking

    if movie_title not in FILM_SUGGESTIONS:
        await update.message.reply_text(f"'{movie_title}' is not in the current film suggestions list.")
        return

    if remove_film_suggestion_and_save(movie_title):
        await update.message.reply_text(f"✅ Film '{movie_title}' has been removed from suggestions.")
    else:
        await update.message.reply_text(f"❌ Failed to remove film '{movie_title}'. Please check logs for errors.")

async def remove_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = update.effective_user.id

    if ADMIN_USER_ID is None:
        await update.message.reply_text("Admin User ID is not configured. /removetheme command is disabled.")
        return
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text(
            "Please provide the exact theme to remove. Example:\n"
            "/removetheme Sci-Fi Classics"
        )
        return

    theme_suggestion = " ".join(context.args).strip()

    load_all_data() # Ensure global list is up-to-date for checking

    if theme_suggestion not in THEME_SUGGESTIONS:
        await update.message.reply_text(f"'{theme_suggestion}' is not in the current theme suggestions list.")
        return

    if remove_theme_suggestion_and_save(theme_suggestion):
        await update.message.reply_text(f"✅ Theme '{theme_suggestion}' has been removed from suggestions.")
    else:
        await update.message.reply_text(f"❌ Failed to remove theme '{theme_suggestion}'. Please check logs for errors.")


async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            continue

        member_name = member.first_name
        if member.last_name:
            member_name += f" {member.last_name}"

        chat_name = update.effective_chat.title if update.effective_chat.title else "this chat"

        welcome_message = (
            f"Hello, {member_name}! 👋 Welcome to {chat_name}!\n"
            "I'm Cleo, your Club 5 to 7 companion. Use /help to see available commands."
        )
        await update.message.reply_text(welcome_message)

# --- FastAPI Application ---
app = FastAPI()

@app.post("/webhook")
async def telegram_webhook(update_dict: dict):
    # Pass the dictionary directly to Update.de_json
    try:
        tg_update = Update.de_json(update_dict, application.bot)
        await application.update_queue.put(tg_update)
    except Exception as e:
        print(f"Error processing webhook update: {e}")
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Telegram bot webhook server is running."}

async def run_server():
    global application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("meetup", meetup_command))
    application.add_handler(CommandHandler("setmeetup", setmeetup_command))
    application.add_handler(CommandHandler("suggestfilm", suggest_film))
    application.add_handler(CommandHandler("suggestionsfilm", show_film_suggestions))
    application.add_handler(CommandHandler("suggesttheme", suggest_theme))
    application.add_handler(CommandHandler("suggestionstheme", show_theme_suggestions))

    # --- NEW Command Handlers (for removal) ---
    application.add_handler(CommandHandler("removefilm", remove_film))
    application.add_handler(CommandHandler("removetheme", remove_theme))

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))

    # --- Initialize and Load Data Based on STORAGE_TYPE ---
    if STORAGE_TYPE == "postgresql":
        if DATABASE_URL:
            initialize_db() # Create tables if they don't exist
            load_all_data() # Load initial data from DB
        else:
            print("WARNING: STORAGE_TYPE is 'postgresql' but DATABASE_URL is not set. Data will not be persistent.")
            reset_to_defaults()
    elif STORAGE_TYPE == "json":
        print("Using JSON file for storage. Remember this requires a persistent disk on Render for production.")
        load_all_data() # Load initial data from JSON
    else:
        print(f"Invalid STORAGE_TYPE '{STORAGE_TYPE}'. Persistence is disabled. Using in-memory defaults.")
        reset_to_defaults()


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

if __name__ == '__main__':
    asyncio.run(run_server())