from aiogram import types, Router
from utils import contains_link, contains_abuse, is_forwarded, is_admin, delete_later, warn_user

router = Router()

@router.message()
async def group_guard(message: types.Message):
    # Work only in groups/supergroups
    if message.chat.type not in ("group", "supergroup"):
        return

    # Skip messages from admins
    if await is_admin(message.chat, message.from_user.id):
        return

    # 1️⃣ Remove links
    if contains_link(message):
        await message.delete()
        warn = await warn_user(message.chat.id, message.from_user.id)
        msg = await message.answer(
            f"🚫 {message.from_user.mention_html()} — sending links is not allowed! (warn {warn}/3)",
            parse_mode="HTML"
        )
        await delete_later(msg)
        return

    # 2️⃣ Remove forwarded messages
    if is_forwarded(message):
        await message.delete()
        warn = await warn_user(message.chat.id, message.from_user.id)
        msg = await message.answer(
            f"🚫 {message.from_user.mention_html()} — forwarding messages is not allowed! (warn {warn}/3)",
            parse_mode="HTML"
        )
        await delete_later(msg)
        return

    # 3️⃣ Delete abusive messages
    if contains_abuse(message):
        await message.delete()
        warn = await warn_user(message.chat.id, message.from_user.id)
        msg = await message.answer(
            f"⚠️ {message.from_user.mention_html()} — please avoid using abusive words! (warn {warn}/3)",
            parse_mode="HTML"
        )
        await delete_later(msg)
        return
