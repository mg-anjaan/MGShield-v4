from aiogram import Router, Bot, F
from aiogram.types import ChatMemberUpdated, Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

# Import utilities
from .utils import delete_later, get_welcome_message, set_welcome_message, is_admin

router = Router()

# --- COMMAND: Set Custom Welcome Message ---
@router.message(Command("setwelcome"))
async def cmd_set_welcome(message: Message, bot: Bot):
    chat_id = message.chat.id

    if message.chat.type not in ["group", "supergroup"]:
        return await message.reply("This command only works in groups.")
        
    if not await is_admin(bot, chat_id, message.from_user.id):
        return await message.reply("⚠️ Only admins can set the welcome message.")

    parts = message.text.split(maxsplit=1)
    new_message = parts[1].strip() if len(parts) > 1 else None

    if not new_message:
        return await message.reply("Usage: `/setwelcome <Your message here>`. Use `{user_name}` as a placeholder for the user's name.", parse_mode="Markdown")

    try:
        await set_welcome_message(chat_id, new_message)
        # Use Markdown for placeholder emphasis
        await message.reply(f"✅ Welcome message saved! New message:\n\n`{new_message}`", parse_mode="Markdown")
    except Exception:
         await message.reply("❌ An error occurred while saving the welcome message to the database.")
         
    await delete_later(message, 10)


# --- HANDLER: Send Welcome Message on Join ---
@router.chat_member(F.new_chat_member.is_member) # Only process status change TO 'member'
async def on_user_join(event: ChatMemberUpdated):
    new = event.new_chat_member
    chat_id = event.chat.id
    
    # Only greet users, not the bot itself
    if new.user.id == event.bot.id:
        return
    
    # 1. Fetch custom message
    custom_msg = await get_welcome_message(chat_id)

    # 2. Format the message
    user_name = new.user.full_name or new.user.first_name or 'there'
    # Use HTML for better formatting of the user's name
    final_msg = custom_msg.replace('{user_name}', f"<b>{user_name}</b>") 
    
    # 3. Send and schedule deletion
    try:
        sent = await event.bot.send_message(chat_id, final_msg, parse_mode="HTML")
        await delete_later(sent, 10)
    except Exception:
         pass # Silently fail if unable to send/delete

# Registration function
def setup_welcome(dp: Router):
    dp.include_router(router)
