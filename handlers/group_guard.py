from aiogram import Dispatcher
from aiogram.types import Message, ChatType
from utils import is_admin, contains_link, contains_abuse, is_forwarded, delete_later

def setup_group_guard(dp: Dispatcher):
    @dp.message()
    async def guard(message: Message):
        # Only run in groups
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return

        # Admins are fully exempt
        if await is_admin(message.chat, message.from_user.id):
            return

        # Forwarded messages block
        if is_forwarded(message):
            await message.reply("⚠️ Forwarded messages are not allowed here.")
            await delete_later(message, 10)
            try:
                await message.delete()
            except:
                pass
            return

        # Link block
        if contains_link(message):
            await message.reply("⚠️ Links are not allowed here!")
            await delete_later(message, 10)
            try:
                await message.delete()
            except:
                pass
            return

        # Abusive word filter (Hindi + English)
        if contains_abuse(message):
            await message.reply("⚠️ Please avoid abusive language.")
            await delete_later(message, 10)
            try:
                await message.delete()
            except:
                pass
            return

        # Simple flood control placeholder (expand as needed)
