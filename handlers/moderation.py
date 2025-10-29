from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
from utils import is_admin, extract_target_user, delete_later, warn_user


def setup_moderation(dp: Dispatcher):

    # 🟢 /mute command
    @dp.message(Command("mute"))
    async def cmd_mute(message: Message):
        if not await is_admin(message.chat, message.from_user.id):
            await message.reply("⚠️ You must be an admin to use this.")
            return

        target = extract_target_user(message)
        if not target:
            await message.reply("Usage: /mute @user 10m")
            return

        user_id, seconds = target

        if await is_admin(message.chat, user_id):
            await message.reply("⚠️ I cannot mute admin.")
            return

        await message.chat.restrict(
            user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=seconds
        )
        await message.reply("🔇 User muted.")
        await delete_later(message, 10)

    # 🟢 /unmute command
    @dp.message(Command("unmute"))
    async def cmd_unmute(message: Message):
        if not await is_admin(message.chat, message.from_user.id):
            await message.reply("⚠️ You must be an admin to use this.")
            return

        target = extract_target_user(message)
        if not target:
            await message.reply("Usage: /unmute @user")
            return

        user_id, _ = target

        await message.chat.restrict(
            user_id,
            permissions=ChatPermissions(can_send_messages=True)
        )
        await message.reply("🔊 User unmuted.")
        await delete_later(message, 10)

    # 🟢 /ban command
    @dp.message(Command("ban"))
    async def cmd_ban(message: Message):
        if not await is_admin(message.chat, message.from_user.id):
            await message.reply("⚠️ You must be an admin to use this.")
            return

        target = extract_target_user(message)
        if not target:
            await message.reply("Usage: /ban @user")
            return

        user_id, _ = target

        if await is_admin(message.chat, user_id):
            await message.reply("⚠️ I cannot ban admin.")
            return

        await message.chat.ban(user_id)
        await message.reply("⛔ User banned.")
        await delete_later(message, 10)

    # 🟢 /unban command
    @dp.message(Command("unban"))
    async def cmd_unban(message: Message):
        if not await is_admin(message.chat, message.from_user.id):
            await message.reply("⚠️ You must be an admin to use this.")
            return

        target = extract_target_user(message)
        if not target:
            await message.reply("Usage: /unban @user")
            return

        user_id, _ = target

        await message.chat.unban(user_id)
        await message.reply("✅ User unbanned.")
        await delete_later(message, 10)

    # 🟢 /warn command
    @dp.message(Command("warn"))
    async def cmd_warn(message: Message):
        if not await is_admin(message.chat, message.from_user.id):
            await message.reply("⚠️ You must be an admin to use this.")
            return

        target = extract_target_user(message)
        if not target:
            await message.reply("Usage: /warn @user")
            return

        user_id, _ = target

        if await is_admin(message.chat, user_id):
            await message.reply("⚠️ I cannot warn admin.")
            return

        warns = await warn_user(message.chat.id, user_id)

        if warns >= 3:
            await message.chat.kick(user_id)
            await message.reply(f"❗ User kicked after {warns} warns.")
        else:
            await message.reply(f"⚠️ User warned ({warns}/3).")

        await delete_later(message, 10)
