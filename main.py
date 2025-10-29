import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command

# ===== HANDLERS =====
from handlers.group_guard import setup_group_guard
from handlers.moderation import setup_moderation
from handlers.admin_tag import setup_admin_tag
from handlers.welcome import setup_welcome

# ===== BOT TOKEN =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN not found! Set it in Render environment variables.")
    exit()

# ===== INIT BOT =====
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# ===== REGISTER HANDLERS =====
setup_group_guard(dp)
setup_moderation(dp)
setup_admin_tag(dp)
setup_welcome(dp)

# ===== TEST COMMAND =====
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("🤖 Bot is running and ready to protect your group!")

# ===== SMALL WEB SERVER FOR RENDER =====
async def handle(request):
    return web.Response(text="✅ MGShield bot is alive and running!")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Web server started on port {port}")

# ===== MAIN =====
async def main():
    print("🚀 Bot is starting...")
    # Start web server first
    await start_web()
    # Then start polling (single instance)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



