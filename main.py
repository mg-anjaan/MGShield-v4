import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Import all handlers through __init__.py
from handlers import register_handlers

# === BOT TOKEN & WEBHOOK SETUP ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not set in environment variables.")

RENDER_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if not RENDER_HOSTNAME:
    raise ValueError("❌ RENDER_EXTERNAL_HOSTNAME not found! Make sure you're on Render environment.")

WEBHOOK_URL = f"https://{RENDER_HOSTNAME}/webhook"

# === INITIALIZE BOT & DISPATCHER ===
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# === TEST HANDLER (/start) ===
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("✅ MGShield is online and running smoothly via webhook!")

# === DEBUG MESSAGE LOGGING ===
@dp.message()
async def all_msg(message: types.Message):
    print(f"📩 Message received: {message.text}")

# === REGISTER ALL FEATURE HANDLERS ===
register_handlers(dp)

# === LIFECYCLE EVENTS ===
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"🚀 Webhook set to {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()
    print("🛑 Bot shutdown")

# === SIMPLE PING ROUTE (for uptime) ===
async def handle_ping(request):
    return web.Response(text="OK")

# === CREATE WEB APP ===
def create_app():
    app = web.Application()
    app.router.add_get("/ping", handle_ping)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

# === ENTRY POINT ===
if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
