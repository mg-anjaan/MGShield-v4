from aiogram import Dispatcher
from aiogram.types import Message
# Ensure these imports are correct based on your utils.py file
from utils import contains_link, contains_abuse, is_admin, delete_later 

async def delete_and_notify(message: Message, reason: str):
    """Deletes the message and sends a short warning."""
    try:
        # Delete the violating message
        await message.delete() 
        
        # Send a warning message and schedule it for deletion
        warning = await message.chat.send_message(
            f"🚫 **{message.from_user.full_name}**, your message was deleted due to **{reason}**.",
            parse_mode="Markdown"
        )
        await delete_later(warning, 10) 
    except Exception:
        # Ignore errors if the bot lacks permissions
        pass

def setup_filters(dp: Dispatcher):
    """Registers a handler to check all messages for prohibited content."""

    @dp.message()
    async def content_filter(message: Message):
        # Skip private chats
        if message.chat.type not in ["group", "supergroup"]:
            return
        
        # Skip admins
        if await is_admin(message.chat, message.from_user.id):
            return
        
        # --- FILTERS ---
        
        # Anti-Link Check
        if contains_link(message):
            await delete_and_notify(message, "prohibited links")
            return  # Stop processing here!
            
        # Anti-Abuse Check
        if contains_abuse(message):
            await delete_and_notify(message, "abusive language")
            return  # Stop processing here!
            
        # If no violation, continue to the next handler (e.g., flood control)
        # return is implicit here
