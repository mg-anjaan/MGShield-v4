import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import Message

# ===== HANDLERS - SIMPLIFIED IMPORT! =====
from handlers import register_all_handlers 

# ===== BOT TOKEN & INIT CHECK (CRITICAL) =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN not found! Set it in Render environment variables.")
    exit(1)

# ===== INIT BOT AND DISPATCHER =====
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# ===== REGISTER HANDLERS =====
register_all_handlers(dp)

# ===== TEST COMMAND =====
@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("🤖 Bot is running and ready to protect your group!")

# ===== SMALL WEB SERVER FOR RENDER (HEALTH CHECK) =====
async def handle(request):
    """Simple handler for the root path (/) to confirm the service is running."""
    return web.Response(text="✅ MGShield bot is alive and running!")

async def start_web():
    """Binds to 0.0.0.0 and the PORT environment variable provided by Render."""
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080)) 
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Web server started on port {port}")

# ===== MAIN APPLICATION RUNNER (POLLING) =====
async def main():
    print("🚀 Bot is starting...")
    
    # 1. Start web server first
    await start_web() 
    
    # 2. 🔥 CONFLICT FIX: Delete existing connections before starting polling
    print("🗑️ Clearing old webhook/polling sessions...")
    await bot.delete_webhook(drop_pending_updates=True) 
    
    # 3. Then start polling (single instance)
    print("📡 Starting Long Polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot stopped manually.")
    except Exception as e:
        print(f"🛑 An unexpected error occurred: {e}")
