import os
import asyncio
import logging
import sqlite3
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.filters import Command
from aiogram.types import ChatPermissions

# --- Import Handlers & Utilities ---
# NOTE: Ensure you have a 'handlers' directory or use the original import style:
from .moderation import setup_moderation
from .group_guard import setup_group_guard
from .admin_tag import setup_admin_tag
from .welcome import setup_welcome
from .filters import setup_filters
from utils import init_db, DB_NAME, delete_later # We'll define init_db in utils.py

# --- Configuration and Initialization ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL")
if not BOT_TOKEN:
    logger.error("🚫 BOT_TOKEN environment variable not set.")
if not REDIS_URL:
    logger.warning("⚠️ REDIS_URL not set. Flood control will use in-memory storage (unstable on Railway).")


# Initialize Bot and Dispatcher
bot = Bot(token=BOT_TOKEN, parse_mode='HTML')

# Initialize Redis Storage for FSM and Rate Limiting
if REDIS_URL:
    # Example parsing logic for aiogram's RedisStorage (may need adjustments based on Redis URL format)
    import urllib.parse
    redis_url_parts = urllib.parse.urlparse(REDIS_URL)
    storage = RedisStorage.from_url(REDIS_URL)
    logger.info("✅ Redis storage initialized for FSM and Flood Control.")
else:
    from aiogram.fsm.storage.memory import MemoryStorage
    storage = MemoryStorage()
    logger.warning("⚠️ Using MemoryStorage. FSM and Flood Control will be unstable.")

dp = Dispatcher(storage=storage)

def register_all_handlers(dp):
    """Registers all feature handlers with the Dispatcher."""
    # 1. Filters and Guards FIRST (These delete/restrict messages)
    setup_filters(dp)
    setup_group_guard(dp) # Will use Redis via dp.storage for persistence

    # 2. Command Handlers and Specific Updates (These handle commands)
    setup_moderation(dp)
    setup_admin_tag(dp)
    setup_welcome(dp) # Will use SQLite via utils.py for persistence

# --- Main Execution ---
async def main():
    if not BOT_TOKEN:
        logger.error("🚫 Cannot start bot: BOT_TOKEN is missing.")
        return

    logger.info("🚀 Bot is starting...")
    
    # 1. Initialize Database (for Warnings and Settings)
    init_db() 

    # 2. Register all handlers
    register_all_handlers(dp)
    
    # 3. Clear stale sessions and start polling
    logger.info("📡 Starting Long Polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Fatal error during long polling: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}")
