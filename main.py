import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import Message

# ===== HANDLERS - SIMPLIFIED IMPORT! =====
# This line replaces all individual handler imports (e.g., from handlers.moderation import setup_moderation)
from handlers import register_all_handlers 

# ===== BOT TOKEN & INIT CHECK (CRITICAL) =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    # This message will be visible in the Render logs if the BOT_TOKEN is missing
    print("❌ BOT_TOKEN not found! Set it in Render environment variables.")
    # Exits the application if the token is missing, preventing a failed deploy loop
    exit(1)

# ===== INIT BOT AND DISPATCHER =====
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# ===== REGISTER HANDLERS (CLEANED UP) =====
# This single call registers all your handlers (moderation, group_guard, filters, etc.)
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
    # Get the port from Render's environment variable (defaults to 8080)
    port = int(os.getenv("PORT", 8080)) 
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Web server started on port {port}")

# ===== MAIN APPLICATION RUNNER (POLLING) =====
async def main():
    print("🚀 Bot is starting...")
    # 1. Start web server first for Render to confirm service is healthy
    await start_web()
    # 2. Then start polling (using Long Polling is simpler than webhooks for aiogram)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot stopped manually.")
    except Exception as e:
        print(f"🛑 An unexpected error occurred: {e}")
