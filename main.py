import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.bot import DefaultBotProperties
from handlers import register_handlers, cleanup_on_shutdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("BOT_TOKEN missing in env. Set it in Render environment variables.")
    raise SystemExit(1)

# Optional comma-separated admin IDs from env (can be empty)
ADMIN_IDS = os.getenv("ADMIN_IDS", "")
ADMIN_IDS_LIST = [int(x) for x in ADMIN_IDS.split(",") if x.strip()]

async def main():
    default_props = DefaultBotProperties(parse_mode="HTML")
    bot = Bot(token=BOT_TOKEN, default=default_props)
    dp = Dispatcher(storage=MemoryStorage())

    # register handlers (pass admin ids list)
    register_handlers(dp, bot, admin_ids=ADMIN_IDS_LIST)

    logging.info("✅ GuardianX is active and watching your groups (logs only). Starting polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await cleanup_on_shutdown(dp, bot)
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
