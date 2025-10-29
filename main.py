import os
import asyncio
from aiogram import Bot, Dispatcher
from aiohttp import web

# Import handlers
from handlers.group_guard import setup_group_guard
from handlers.moderation import setup_moderation
from handlers.admin_tag import setup_admin_tag
from handlers.welcome import setup_welcome

# ------------------ BOT SETUP ------------------ #
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN not set. Set it in Render environment variables.")
    exit(1)

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# Register handlers
setup_group_guard(dp)
setup_moderation(dp)
setup_admin_tag(dp)
setup_welcome(dp)

# ------------------ SERVER HANDLER ------------------ #
async def handle_ping(request):
    return web.Response(text="OK")

def create_app():
    app = web.Application()
    app.add_routes([web.get("/ping", handle_ping)])
    return app

# ------------------ LIFECYCLE EVENTS ------------------ #
async def on_startup():
    print("🚀 Bot is starting...")

async def on_shutdown():
    await bot.session.close()
    print("🛑 Bot is shutting down...")

# ------------------ MAIN ENTRY ------------------ #
if __name__ == "__main__":
    async def main():
        # Start aiohttp web server
        app = create_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "8080")))
        await site.start()
        print("🌐 Web server running for self-ping...")

        # Start bot polling
        await on_startup()
        try:
            await dp.start_polling(bot)
        finally:
            await on_shutdown()

    asyncio.run(main())


