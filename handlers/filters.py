from aiogram import Dispatcher, types
from aiogram.types import Message
from utils import contains_link, contains_abuse, is_admin

async def delete_and_notify(message: Message, reason: str):
    """Deletes the violating message and sends a warning notification."""
    try:
        await message.delete()
        # You may want to customize this warning message
        warning = await message.chat.send_message(
            f"🚫 **{message.from_user.full_name}**, your message was deleted due to **{reason}**."
        )
        # Assuming you have delete_later in utils.py, you can use it here:
        # from utils import delete_later
        # await delete_later(warning, 10) 
        # For simplicity, we'll keep it as a standard send for now
    except Exception:
        # Ignore errors if the bot can't delete the message (e.g., lack of admin rights)
        pass

def setup_filters(dp: Dispatcher):
    """Registers a handler to check all messages for prohibited content."""

    @dp.message()
    async def content_filter(message: Message):
        # 1. Skip checks if in a private chat
        if message.chat.type not in ["group", "supergroup"]:
            return
        
        # 2. Skip checks for administrators (optional, but standard practice)
        if await is_admin(message.chat, message.from_user.id):
            return
        
        # --- FILTERS ---
        
        # Anti-Link Check
        if contains_link(message):
            await delete_and_notify(message, "prohibited links")
            # Stop processing this update once a violation is found
            return 
            
        # Anti-Abuse Check
        if contains_abuse(message):
            # You might choose to use the /warn feature here instead of just deleting
            # from utils import warn_user
            # warns = await warn_user(message.chat.id, message.from_user.id)
            # if warns >= 3: ... kick logic ...
            
            await delete_and_notify(message, "abusive language")
            return 
            
        # Placeholder for other checks (e.g., Anti-Forward, Anti-Sticker, etc.)
        
        # If all checks pass, the message is allowed
        return
