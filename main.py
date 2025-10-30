import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from dotenv import load_dotenv

# Load environment variables (important for local testing, harmless on Railway)
load_dotenv()

# --- Configuration ---
# Your bot token is taken from Railway environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # Used for specific admin features

# Redis connection details. We prioritize REDIS_URL which usually contains the IP.
# If REDIS_URL is not found, we fall back to the Railway service name "redis".
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379") 

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Initialization Functions ---

def setup_redis():
    """Initializes the Redis client using the environment variable."""
    logger.info(f"Initializing Redis connection using URL: {REDIS_URL}")
    
    # aiogram's RedisStorage can take a Redis object initialized from a URL
    redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
    storage = RedisStorage(redis=redis_client)
    
    return redis_client, storage

async def main():
    """Main function to initialize and start the bot."""
    if not BOT_TOKEN:
        logger.error("FATAL: TELEGRAM_BOT_TOKEN not found in environment variables.")
        return

    # 1. Setup Redis and Storage
    redis_client, storage = setup_redis()
    
    # CRITICAL: Test Redis connection on startup to catch DNS/IP errors early
    try:
        await redis_client.ping()
        logger.info("✅ Redis connection established successfully.")
    except Exception as e:
        logger.error(f"❌ Redis PING failed on startup. Bot will likely fail later. Error: {e}")
        # We proceed, but logging the failure is important

    # 2. Setup Bot and Dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=storage)

    # 3. Register Routers (Handlers)
    # You must import and register your handlers here!
    
    # Example: If your filters.py has a router named 'filters_router'
    # from .handlers import filters
    # dp.include_router(filters.filters_router) 
    
    logger.info("Bot handlers and middleware initialized.")

    # 4. Clear old webhooks and start polling
    try:
        # Clear any residual Telegram webhooks or polling conflicts
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Telegram webhook cleared. Starting polling...")
        
        # Start the bot. This is the main blocking call.
        await dp.start_polling(bot)
        
    finally:
        # Graceful shutdown
        await bot.session.close()
        await storage.close()
        logger.info("Bot stopped gracefully.")


if __name__ == "__main__":
    logger.info("Starting GroupGuardian Bot...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down due to interrupt.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during bot runtime: {e}")
