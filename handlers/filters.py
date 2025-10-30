from aiogram import Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
# Ensure these imports are correct based on your utils.py file
from utils import contains_link, contains_abuse, is_admin, delete_later 
from aiogram.filters import CommandObject
from aiogram.utils.deep_linking import decode_payload

# --- Helper Function (Keep this the same) ---
async def delete_and_notify(message: Message, reason: str):
    try:
        await message.delete() 
        warning = await message.chat.send_message(
            f"🚫 **{message.from_user.full_name}**, your message was deleted due to **{reason}**.",
            parse_mode="Markdown"
        )
        await delete_later(warning, 10) 
    except Exception:
        pass

# --- Filter Function (Returns True if message should be SKIPPED) ---
async def check_if_admin_or_bot(message: Message) -> bool:
    """Returns True if the user is an admin or a bot (meaning the filter should skip them)."""
    if message.chat.type not in ["group", "supergroup"]:
        return True # Skip private chats from filter logic
    if message.from_user.is_bot:
        return True
    return await is_admin(message.chat, message.from_user.id)

# --- Main Setup Function ---
def setup_filters(dp: Dispatcher):
    """Registers a set of handlers for anti-spam, anti-link, and the final catch-all."""
    
    # ----------------------------------------------------------------------
    # 1. ANTI-SPAM / ANTI-LINK HANDLER (Highest priority within this router)
    # ----------------------------------------------------------------------
    
    @dp.message(
        F.text,                                       # Must have text
        ~F.func(check_if_admin_or_bot),               # ✅ FIX: Invert the result of the function
        
        # CRITICAL FILTER: Only check messages that contain a link or abuse
        (F.text.func(contains_link) | F.text.func(contains_abuse))
    )
    async def content_filter(message: Message):
        """Checks for prohibited content and deletes the message if found."""
        
        # Anti-Link Check
        if contains_link(message):
            await delete_and_notify(message, "prohibited links")
            return # Stop processing the update here
            
        # Anti-Abuse Check
        if contains_abuse(message):
            await delete_and_notify(message, "abusive language")
            return # Stop processing the update here
            
    # ----------------------------------------------------------------------
    # 2. FINAL CATCH-ALL / UNKNOWN COMMAND HANDLER (Lowest priority in all routers)
    # ----------------------------------------------------------------------

    @dp.message()
    async def unknown_command_or_text_handler(message: Message):
        """
        This handler catches EVERYTHING that wasn't handled by any previous,
        more specific handler (Commands, Specific Content Filters, etc.).
        """
        
        # Skip private chats
        if message.chat.type not in ["group", "supergroup"]:
            return
            
        # If the message is text and starts with '/' but wasn't a recognized command, 
        # it's an UNKNOWN COMMAND.
        if message.text and message.text.startswith('/'):
            await message.reply("Sorry, I don't recognize that command. Use /help to see what I can do.")
            return

        # You can add your general message/echo logic here if needed.
        return
