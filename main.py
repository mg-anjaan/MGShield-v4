import os
import asyncio
import logging
import sqlite3
import re
import urllib.parse
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage # Always import MemoryStorage as fallback
from aiogram.filters import Command

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Import Handlers (FIXED: Using absolute imports for 'handlers' package) ---
from handlers.moderation import setup_moderation
from handlers.group_guard import setup_group_guard
from handlers.admin_tag import setup_admin_tag
from handlers.welcome import setup_welcome
from handlers.filters import setup_filters
from utils import init_db, DB_NAME, delete_later # Assuming these are correct

# --- Configuration and Initialization ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL")

# Initialize Bot
if not BOT_TOKEN:
    logger.error("🚫 BOT_TOKEN environment variable not set. Exiting.")
    exit()
    
bot = Bot(token=BOT_TOKEN, parse_mode='HTML')

# Initialize Storage (Redis for production, Memory for fallback)
if REDIS_URL:
    try:
        storage = RedisStorage.from_url(REDIS_URL)
        logger.info("✅ Redis storage initialized for FSM and Flood Control.")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis using REDIS_URL. Falling back to MemoryStorage. Error: {e}")
        storage = MemoryStorage()
else:
    storage = MemoryStorage()
    logger.warning("⚠️ REDIS_URL not set. Using MemoryStorage. Flood Control will be unstable.")

dp = Dispatcher(storage=storage)

def register_all_handlers(dp):
    """
    Registers all feature handlers with the Dispatcher.
    Order is CRITICAL: Most specific (Commands) first, broadest (Filters/Guards) last.
    """
    
    # 1. COMMAND HANDLERS & SPECIFIC FEATURES (Check /start, /ban, /admin first)
    # If a message is a command, it will be handled here and skip the later, broader filters.
    logger.info("Setting up Command and Specific handlers...")
    setup_moderation(dp) # Commands like /ban, /mute
    setup_admin_tag(dp)  # Specific commands or updates related to admin tags
    setup_welcome(dp)    # Specific update for new member joined

    # 2. BROAD FILTERS and GUARDS (Check for spam, links, and handle general messages last)
    # These contain broad filters (like F.text.contains or the final catch-all)
    # They should only be reached if the message was NOT a command.
    logger.info("Setting up Broad Filters and Guards...")
    setup_filters(dp)     # Spam, Links, Abuse detection, and the final "Unknown Command" catch-all
    setup_group_guard(dp) # General group restrictions

# --- Main Execution ---
async def main():
    logger.info("🚀 Bot is starting...")
    
    # 1. Initialize Database (for Warnings and Settings)
    init_db() 

    # 2. Register all handlers with the corrected order
    register_all_handlers(dp)
    
    # 3. Clear stale sessions and start polling
    logger.info("📡 Starting Long Polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Fatal error during long polling: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}")
