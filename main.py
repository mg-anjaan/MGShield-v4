import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Import all handlers
from handlers.group_guard import setup_group_guard
from handlers.moderation import setup_moderation
from handlers.admin_tag import setup_admin_tag
from handlers.welcome import setup_welcome

# ✅ Import for /start command (universal test)
from aiogram import types
from aiogram.filters import CommandStart

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not set in environment variables.")

WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# ✅ Universal test handler
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("✅ Bot is alive and connected via webhook!")

@dp.message()
async def all_msg(message: types.Message):
    print(f"📩 Message received: {message.text}")
    # just confirm receiving messages
    # uncomment below if needed for debugging
    # await message.answer("✅ Received your message!")

# Register your handlers
setup_group_guard(dp)
setup_moderation(dp)
setup_admin_tag(dp)
setup_welcome(dp)

# Events
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"🚀 Webhook set to {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()
    print("🛑 Bot shutdown")

# Simple ping route (for uptime check)
async def handle_ping(request):
    return web.Response(text="OK")

# Aiohttp app
def create_app():
    app = web.Application()
    app.router.add_get("/ping", handle_ping)

    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
