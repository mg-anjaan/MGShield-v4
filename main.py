import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, Redis
# Import necessary components from your modular structure
from handlers import register_all_handlers
from utils import init_db

# --- Configuration ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# NOTE: Ensure you set these environment variables correctly (e.g., in a .env file or Railway config)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost") 
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379)) 

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting GroupGuardian Bot...")
    
    if not BOT_TOKEN:
        raise ValueError("FATAL: TELEGRAM_BOT_TOKEN environment variable not set.")
    
    # 1. Initialize Database (SQLite)
    init_db()
    logger.info("SQLite database initialized for warnings and settings.")

    # 2. Initialize Redis Storage for FSM and Flood Control
    try:
        redis = Redis(host=REDIS_HOST, port=REDIS_PORT)
        storage = RedisStorage(redis=redis)
        logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}.")
    except Exception as e:
        logger.error(f"FATAL: Redis connection failed: {e}")
        # Flood control is a critical feature that requires Redis
        raise ConnectionError("Redis connection failed. Please ensure Redis is running and configured.")

    # 3. Initialize Bot and Dispatcher
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher(storage=storage)

    # 4. Register all Handlers
    register_all_handlers(dp)
    
    # 5. Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Bot stopped by system signal.")
    except Exception as e:
        logger.error(f"An unhandled error occurred: {e}", exc_info=True)
