import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import register_handlers

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not found! Set it in Render environment variables.")
        return
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())
    register_handlers(dp, bot)
    print("🤖 MGShield v4 started successfully!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
