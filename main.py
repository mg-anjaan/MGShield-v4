# main.py

import os
import asyncio
from aiohttp import web
# ... other imports ...

# === SIMPLIFIED HANDLERS IMPORT ===
from handlers import register_all_handlers # <--- Import the function from __init__.py
# Note: Delete all the individual `from handlers.xxx import setup_xxx` lines!

# ===== BOT TOKEN & INIT BOT =====
# ... (BOT_TOKEN check and dp/bot creation is fine) ...

# ===== REGISTER HANDLERS =====
# Delete all the old setup calls (e.g., setup_group_guard(dp))
# and replace with:
register_all_handlers(dp) # <--- ONE clean call

# ===== WEB SERVER FOR RENDER & MAIN =====
# ... (start_web and main function logic is fine for Render) ...

if __name__ == "__main__":
    asyncio.run(main())

