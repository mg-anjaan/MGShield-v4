from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

# Import utilities
from .utils import is_admin

router = Router()

@router.message(Command("tagall"))
async def tag_admins(message: Message, bot: Bot):
    """Tags all group administrators."""
    chat_id = message.chat.id

    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("❌ This command only works in groups.")
        return

    # Check if user is admin
    if not await is_admin(bot, chat_id, message.from_user.id):
        await message.reply("❌ Only admins can use /tagall.")
        return

    # Get all administrators
    members = []
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for m in admins:
            # Check if the user ID is the bot itself or if the user is anonymous
            if m.user and m.user.id != bot.id:
                # Use mention_html() for correct HTML formatting
                members.append(m.user.mention_html())
    except TelegramBadRequest:
        await message.reply("❌ Bot must be an administrator to fetch the admin list.")
        return
    except Exception:
        await message.reply("❌ An unexpected error occurred while fetching admins.")
        return
        
    if not members:
        await message.reply("No administrators found to tag.")
        return

    tags = " ".join(members)
    try:
        # Use HTML parse_mode for mentions
        await message.answer(f"📢 **Attention Admins:**\n\n{tags}", parse_mode="HTML")
    except Exception:
         await message.answer("An error occurred sending the tags. Check bot permissions.", parse_mode="Markdown")

# Registration function
def setup_admin_tag(dp: Router):
    dp.include_router(router)
