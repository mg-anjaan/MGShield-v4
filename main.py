import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Import all handlers
from handlers.group_guard import setup_group_guard
from handlers.moderation import setup_moderation
from handlers.admin_tag import setup_admin_tag
from handlers.welcome import setup_welcome

# -------------------------------------------------
# 🔧 Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not set in environment variables.")

# Use Render-provided external hostname for webhook
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"

# -------------------------------------------------
# 🔹 Initialize Bot and Dispatcher
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# -------------------------------------------------
# ✅ Simple /start command to confirm bot is alive
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("🤖 Bot is active and connected via webhook!")

# -------------------------------------------------
# 🔍 Optional: Debug print for all messages
@dp.message()
async def all_msg(message: types.Message):
    print(f"📩 Message from {message.from_user.id}: {message.text}")

# -------------------------------------------------
# 🔧 Register all custom handlers
setup_group_guard(dp)     # Spam, flood, link, abusive filter
setup_moderation(dp)      # Mute, unmute, ban, unban, warn
setup_admin_tag(dp)       # Admin tag mention
setup_welcome(dp)         # Welcome message

# -------------------------------------------------
# 🚀 Webhook events
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"🚀 Webhook set to {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()
    print("🛑 Bot shutdown")

# -------------------------------------------------
# 🌐 Health check route
async def handle_ping(request):
    return web.Response(text="OK")

# -------------------------------------------------
# 🧩 Create aiohttp app for webhook
def create_app():
    app = web.Application()
    app.router.add_get("/ping", handle_ping)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

# -------------------------------------------------
# ▶️ Local run support (for Render too)
if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))


