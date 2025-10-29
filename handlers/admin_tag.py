from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from utils import admins_list, delete_later

def setup_admin_tag(dp: Dispatcher):
    @dp.message(Command(["tagall","all"]))
    async def tag_all(message: Message):
        # admin-only
        admin_ids = await admins_list(message.chat)
        if message.from_user.id not in [int(a.split(':')[-1]) if ':' in a else a for a in admin_ids]:
            await message.reply("⚠️ Only admins can use this.")
            return
        # Build a short mention list (first names)
        text = "🔔 Admins:\n"
        for a in admin_ids:
            text += f"- {a}\n"
        await message.reply(text)
        await delete_later(message, 10)
