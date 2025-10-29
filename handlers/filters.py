from aiogram import Dispatcher
from aiogram.types import Message, Message
# Ensure these imports are correct based on your utils.py file
from utils import contains_link, contains_abuse, is_admin, delete_later 
from aiogram.filters import CommandObject
from aiogram.utils.deep_linking import decode_payload

async def delete_and_notify(message: Message, reason: str):
    # (The body of this function remains the same as before)
    try:
        await message.delete() 
        warning = await message.chat.send_message(
            f"🚫 **{message.from_user.full_name}**, your message was deleted due to **{reason}**.",
            parse_mode="Markdown"
        )
        await delete_later(warning, 10) 
    except Exception:
        pass

def setup_filters(dp: Dispatcher):
    """Registers a handler to check all messages for prohibited content."""

    # Note: We are keeping the generic @dp.message() but adding an early return for commands
    @dp.message()
    async def content_filter(message: Message):
        # 1. Skip private chats
        if message.chat.type not in ["group", "supergroup"]:
            return
        
        # 2. Skip admins
        # Check if the user is an admin or if the message is from the bot itself
        if await is_admin(message.chat, message.from_user.id) or message.from_user.is_bot:
            return
            
        # 3. CRITICAL FIX: Skip messages that ARE commands!
        # If the message text starts with '/' (and is not an edit), assume it's a command
        if message.text and message.text.startswith('/'):
            # Allow the message to pass to the next handler (the command handlers)
            return 

        # --- FILTERS (Only runs for non-admin, non-command messages) ---
        
        # Anti-Link Check
        if contains_link(message):
            await delete_and_notify(message, "prohibited links")
            return  # Stop processing here!
            
        # Anti-Abuse Check
        if contains_abuse(message):
            await delete_and_notify(message, "abusive language")
            return  # Stop processing here!
            
        # If all checks pass, the message continues to flood control, then stops.
        return
