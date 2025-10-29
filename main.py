import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from handlers.group_guard import setup_group_guard
from handlers.moderation import setup_moderation
from handlers.admin_tag import setup_admin_tag
from handlers.welcome import setup_welcome

# -------------------------------------------------
# 🔧 Load BOT_TOKEN from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN not found! Set it in Render environment variables.")
    exit()

# -------------------------------------------------
# 🔹 Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# -------------------------------------------------
# ✅ Register all handlers
setup_group_guard(dp)
setup_moderation(dp)
setup_admin_tag(dp)
setup_welcome(dp)

# -------------------------------------------------
# ▶️ Start command for test
from aiogram import types
from aiogram.filters import Command

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("🤖 Bot is running and ready to protect your group!")

# -------------------------------------------------
# 🚀 Run bot using polling (Render supported)
async def main():
    print("✅ Bot is starting with polling mode...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


