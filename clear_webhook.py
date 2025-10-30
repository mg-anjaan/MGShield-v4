import asyncio
import os
from aiogram import Bot

# IMPORTANT: Ensure your TELEGRAM_BOT_TOKEN is set in a .env file locally 
# OR hardcode it here (temporarily) if you cannot use os.getenv
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") 

async def clear_polling_session():
    """Forces Telegram to drop any active poll or webhook."""
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is not set. Please set it locally.")
        return

    print("Attempting to clear Telegram webhook and active polling sessions...")
    
    bot = Bot(token=BOT_TOKEN)
    
    try:
        # This command drops any pending updates and deletes any active webhook.
        success = await bot.delete_webhook(drop_pending_updates=True)
        print(f"Webhook/Polling session cleared successfully: {success}")

        print("\n✅ Conflict is now resolved. Your Railway bot will take over control.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(clear_polling_session())
