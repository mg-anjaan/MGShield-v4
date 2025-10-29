from aiogram import types
from aiogram.filters import Command
from aiogram.types import Message

def setup_admin_tag(dp):
    @dp.message(Command("tagall"))
    async def tag_all(message: Message):
        if message.chat.type not in ["group", "supergroup"]:
            await message.reply("❌ This command only works in groups.")
            return

        # Check if user is admin
        member = await message.chat.get_member(message.from_user.id)
        if member.status not in ["administrator", "creator"]:
            await message.reply("❌ Only admins can tag everyone.")
            return

        # Get all members (limited by Telegram API)
        members = []
        async for m in message.chat.get_administrators():
            members.append(m.user.mention_html())

        if not members:
            await message.reply("No members found to tag.")
            return

        tags = " ".join(members)
        await message.reply(f"👥 Tagging everyone:\n\n{tags}", parse_mode="HTML")
