from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

# Import utilities
from utils import contains_link, contains_abuse, is_admin, delete_later, warn_user, check_for_kick
router = Router()

# --- Helper Function (Includes Warning/Kick Logic) ---
async def delete_and_warn(message: Message, reason: str):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # 1. Delete and Notify
    try:
        await message.delete() 
        warning_msg = await message.chat.send_message(
            f"🚫 **{message.from_user.full_name}**, your message was deleted due to **{reason}** and you received a warning.",
            parse_mode="Markdown"
        )
        await delete_later(warning_msg, 10) 
    except Exception:
        pass

    # 2. Issue Warning and Check for Kick
    new_warns = await warn_user(chat_id, user_id)
    await check_for_kick(message, new_warns)


# --- ANTI-SPAM / ANTI-LINK HANDLER ---
# Processes messages that contain text, photo, or video (to check captions/entities)
@router.message(
    F.text | F.caption | F.photo | F.video, 
    ~F.text.startswith('/') 
)
async def content_filter(message: Message, bot: Bot):
    """Checks for prohibited content (links, abuse) and deletes/warns the user."""
    
    # 1. Primary Check: Skip Admins/Bots
    if message.from_user.is_bot:
        return
    if await is_admin(bot, message.chat.id, message.from_user.id):
        return

    # 2. Anti-Link Check
    if contains_link(message):
        await delete_and_warn(message, "prohibited links")
        return
            
    # 3. Anti-Abuse Check
    if contains_abuse(message):
        await delete_and_warn(message, "abusive language")
        return
            
# --- FINAL CATCH-ALL / UNKNOWN COMMAND HANDLER (Lowest Priority) ---
# NOTE: This must be the LAST handler included in the Dispatcher.
@router.message()
async def unknown_command_or_text_handler(message: Message):
    """Catches unknown commands."""
    
    if message.chat.type not in ["group", "supergroup"]:
        return
            
    if message.text and message.text.startswith('/'):
        # Ignore messages from bots/self
        if message.from_user.is_bot or message.from_user.id == message.bot.id:
             return
             
        await message.reply("Sorry, I don't recognize that command. Use /help to see what I can do.")
        return

# Registration function
def setup_filters(dp: Router):
    dp.include_router(router)
