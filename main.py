import os
import asyncio
from aiogram import Bot, Dispatcher
from aiohttp import web

from handlers.group_guard import setup_group_guard
from handlers.moderation import setup_moderation
from handlers.admin_tag import setup_admin_tag
from handlers.welcome import setup_welcome

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN not set. Set it in Render environment variables.")
    raise SystemExit

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Register all handlers
setup_group_guard(dp)
setup_moderation(dp)
setup_admin_tag(dp)
setup_welcome(dp)

async def on_startup():
    print("✅ Bot has started successfully!")

async def on_shutdown():
    await bot.session.close()
    print("🛑 Bot is shutting down...")

# For Render ping (keeps app alive)
async def handle_ping(request):
    return web.Response(text="OK")

def create_app():
    app = web.Application()
    app.add_routes([web.get('/', handle_ping), web.get('/ping', handle_ping)])
    return app

async def main():
    await on_startup()

    # Start aiohttp web server (for uptime ping)
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "8080")))
    await site.start()

    # Start polling (this keeps the bot active)
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())

