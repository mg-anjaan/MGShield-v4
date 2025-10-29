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

# ===== REGISTER HANDLERS (Order is critical for filters/commands) =====
# The correct order is inside handlers/__init__.py, which this function calls.
register_all_handlers(dp)

# ===== TEST COMMAND =====
@dp.message(Command("start"))
async def start_cmd(message: Message):
    # This command should now work after the command-skipping fix in filters/guards
    await message.answer("🤖 MGShield bot is running and ready to protect your group!")

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
    
    # 2. 🔥 ROBUST CONFLICT FIX: Aggressive Webhook Deletion Loop
    print("🗑️ Ensuring old webhook/polling sessions are cleared...")
    
    # Loop 5 times, waiting 1 second between attempts, to forcefully clear the old connection
    for i in range(5):
        try:
            # We call delete_webhook even though we use polling; it clears *any* active session.
            await bot.delete_webhook(drop_pending_updates=True)
            print(f"✅ Connection cleared successfully (Attempt {i+1}).")
            break # Exit loop if successful
        except Exception as e:
            # This catches potential network/API issues during the deletion process
            print(f"⚠️ Deletion failed (Attempt {i+1}): {e}. Retrying in 1 second...")
            await asyncio.sleep(1)
    
    # 3. Start polling
    print("📡 Starting Long Polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot stopped manually.")
    except Exception as e:
        print(f"🛑 An unexpected error occurred: {e}")
