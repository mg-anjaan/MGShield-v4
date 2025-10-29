import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiohttp import web

from handlers.group_guard import setup_group_guard
from handlers.moderation import setup_moderation
from handlers.admin_tag import setup_admin_tag
from handlers.welcome import setup_welcome

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN not set. Set it in Render environment variables.")
    # For local testing you can set BOT_TOKEN env var, but bot will not run without it.

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Register handlers
setup_group_guard(dp)
setup_moderation(dp)
setup_admin_tag(dp)
setup_welcome(dp)

async def on_startup():
    print("Bot is starting...")

async def on_shutdown():
    await bot.session.close()
    print("Bot is shutting down...")

# Simple aiohttp server for Render self-ping (Option A)
async def handle_ping(request):
    return web.Response(text="OK")

def create_app():
    app = web.Application()
    app.add_routes([web.get('/ping', handle_ping)])
    return app

if __name__ == "__main__":
    # Run both aiohttp server and aiogram dispatcher
    loop = asyncio.get_event_loop()

    # Start aiohttp in background
    app = create_app()
    runner = web.AppRunner(app)

    async def start_services():
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "8080")))
        await site.start()
        await on_startup()
        # Start polling (Aiogram) - Dispatcher.start_polling blocks so run it as task
        await dp.start_polling(bot)

    try:
        loop.run_until_complete(start_services())
    except (KeyboardInterrupt, SystemExit):
        loop.run_until_complete(on_shutdown())
