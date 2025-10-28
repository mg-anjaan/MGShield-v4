import os
import json
from datetime import datetime, timedelta
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import ChatPermissions

router = Router()
BOT = None
WARNINGS_FILE = "warnings.json"
WARNINGS = {}
WARNINGS_THRESHOLD = 3

def load_warnings():
    global WARNINGS
    if os.path.exists(WARNINGS_FILE):
        try:
            with open(WARNINGS_FILE, "r", encoding="utf-8") as f:
                WARNINGS = json.load(f)
        except:
            WARNINGS = {}
    else:
        WARNINGS = {}

def save_warnings():
    with open(WARNINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(WARNINGS, f, ensure_ascii=False, indent=2)

def warn_key(chat_id, user_id):
    return f"{chat_id}:{user_id}"

async def is_admin(chat_id, user_id):
    try:
        member = await BOT.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except:
        return False

async def apply_mute(chat_id, user_id, minutes):
    until = datetime.utcnow() + timedelta(minutes=minutes)
    perms = ChatPermissions(can_send_messages=False)
    try:
        await BOT.restrict_chat_member(chat_id, user_id, permissions=perms, until_date=until)
        return True
    except:
        return False

async def unmute(chat_id, user_id):
    perms = ChatPermissions(can_send_messages=True)
    try:
        await BOT.restrict_chat_member(chat_id, user_id, permissions=perms)
        return True
    except:
        return False

def mention_html(user: types.User):
    return f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"

async def send_welcome(message: types.Message):
    if not message.new_chat_members:
        return
    for member in message.new_chat_members:
        if member.is_bot:
            continue
        await message.answer(f"👋 Welcome {mention_html(member)} to the group!\n✨ Please follow the rules and be respectful! ✨", parse_mode="HTML")

@router.message()
async def handle_message(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    if message.new_chat_members:
        return await send_welcome(message)
    text = (message.text or "").lower()
    bad_words = ["chutiya", "madarchod", "bhosdike", "gandu", "bitch", "fuck", "lund", "randi", "mc", "bc"]
    if any(bad in text for bad in bad_words):
        try:
            await message.delete()
        except:
            pass
        key = warn_key(message.chat.id, message.from_user.id)
        WARNINGS[key] = WARNINGS.get(key, 0) + 1
        save_warnings()
        count = WARNINGS[key]
        if count >= WARNINGS_THRESHOLD:
            try:
                await BOT.ban_chat_member(message.chat.id, message.from_user.id)
                await message.answer(f"🚫 @admin {mention_html(message.from_user)} has been automatically banned after 3 warnings!", parse_mode="HTML")
            except:
                await message.answer("⚠️ Tried to ban user but failed. Ensure I have admin rights.")
            WARNINGS[key] = 0
            save_warnings()
        else:
            await message.answer(f"⚠️ {mention_html(message.from_user)}, please avoid abusive language! Warning {count}/3.", parse_mode="HTML")

def register_handlers(dp, bot):
    global BOT
    BOT = bot
    load_warnings()
    dp.include_router(router)
