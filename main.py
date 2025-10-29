import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiohttp import web

from handlers.group_guard import setup_group_guard
from handlers.moderation import setup_moderation
from handlers.admin_tag import setup_admin_tag
from handlers.welcome import setup_welcome

# ✅ Your bot token and Render app URL
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = "https://mgshield-v4-1.onrender.com"
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Register all handlers (no feature change)
setup_group_guard(dp)
setup_moderation(dp)
setup_admin_tag(dp)
setup_welcome(dp)

# ---------- Webhook Setup ----------
async def on_startup(app):
    print("🚀 Setting webhook...")
    await bot.set_webhook(WEBHOOK_URL)
    print("✅ Webhook set successfully.")

async def on_shutdown(app):
    print("🛑 Shutting down...")
    await bot.delete_webhook()
    await bot.session.close()

# ---------- Aiohttp Server ----------
async def handle_webhook(request):
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        return web.Response(text="OK")
    except Exception as e:
        print("❌ Error handling update:", e)
        return web.Response(status=500)

# Optional ping route for Render health check
async def handle_ping(request):
    return web.Response(text="PONG")

def create_app():
    app = web.Application()
    app.add_routes([
        web.post(WEBHOOK_PATH, handle_webhook),
        web.get("/ping", handle_ping),
    ])
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
