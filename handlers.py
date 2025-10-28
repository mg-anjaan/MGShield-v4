import os, re, time, json, logging
from collections import defaultdict
from typing import Dict, List, Optional
from aiogram import types, Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message

logging.basicConfig(level=logging.INFO)

WARN_FILE = "warnings.json"
ABUSIVE_FILE = "abusive_words.txt"
WARN_LIMIT = 3
SPAM_THRESHOLD = 5
MUTE_DURATION_SECONDS = 60*60*24*365*10  # ~10 years

# Load abusive words from file (one per line)
def load_abusive():
    if not os.path.exists(ABUSIVE_FILE):
        # create example file
        sample = ["madarchod","behenchod","chutiya","bhosdike","randi","bc","mc","fuck","bitch","asshole"]
        with open(ABUSIVE_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(sample))
        return set(sample)
    with open(ABUSIVE_FILE, "r", encoding="utf-8") as f:
        return set([line.strip().lower() for line in f if line.strip() and not line.strip().startswith('#')])

ABUSIVE = load_abusive()

# Warnings persistence
def load_warns():
    try:
        with open(WARN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_warns(w):
    try:
        with open(WARN_FILE, "w", encoding="utf-8") as f:
            json.dump(w, f)
    except Exception as e:
        logging.error("Failed to save warns: %s", e)

warns = load_warns()  # key = "<chat_id>:<user_id>" -> int

# Spam tracker per chat: { chat_id: { 'last_user': id, 'count': n } }
spam_track: Dict[int, Dict] = defaultdict(lambda: {"last_user": None, "count": 0})

def contains_link_in_message(msg: Message) -> bool:
    # checks entities + caption + text
    if getattr(msg, 'entities', None):
        for e in msg.entities:
            if e.type in ("url", "text_link"):
                return True
    if getattr(msg, 'caption', None) and re.search(r"https?://|t\.me/|telegram\.me/", (msg.caption or ""), re.I):
        return True
    if getattr(msg, 'text', None) and re.search(r"https?://|t\.me/|telegram\.me/", (msg.text or ""), re.I):
        return True
    return False

def contains_abusive_text(text: str) -> bool:
    if not text:
        return False
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = cleaned.split()
    for t in tokens:
        if t in ABUSIVE:
            return True
    return False

def make_key(chat_id: int, user_id: int) -> str:
    return f"{chat_id}:{user_id}"

async def is_admin(bot: Bot, chat_id: int, user_id: int, admin_ids_env: Optional[List[int]] = None) -> bool:
    # check env list first
    if admin_ids_env and user_id in admin_ids_env:
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.is_chat_admin() or member.is_chat_owner()
    except Exception:
        return False

async def restrict_member(bot: Bot, chat_id: int, user_id: int):
    try:
        await bot.restrict_chat_member(chat_id=chat_id, user_id=user_id,
                                      permissions=ChatPermissions(can_send_messages=False,
                                                                  can_send_media_messages=False,
                                                                  can_send_other_messages=False,
                                                                  can_add_web_page_previews=False),
                                      until_date=int(time.time())+MUTE_DURATION_SECONDS)
    except Exception as e:
        logging.error("restrict error: %s", e)

async def unrestrict_member(bot: Bot, chat_id: int, user_id: int):
    try:
        await bot.restrict_chat_member(chat_id=chat_id, user_id=user_id,
                                      permissions=ChatPermissions(can_send_messages=True,
                                                                  can_send_media_messages=True,
                                                                  can_send_other_messages=True,
                                                                  can_add_web_page_previews=True))
    except Exception as e:
        logging.error("unrestrict error: %s", e)

def register_handlers(dp: Dispatcher, bot: Bot, admin_ids: List[int] = None):
    admin_ids = admin_ids or []

    @dp.message()
    async def on_message(message: Message):
        chat = message.chat
        if chat.type not in ("group", "supergroup"):
            return
        user = message.from_user
        uid = user.id

        # If admin, ignore moderation and reset spam sequence
        if await is_admin(bot, chat.id, uid, admin_ids):
            spam_track[chat.id] = {"last_user": None, "count": 0}
            return

        # LINK detection
        if contains_link_in_message(message):
            try:
                await message.delete()
            except Exception:
                pass
            key = make_key(chat.id, uid)
            warns[key] = warns.get(key, 0) + 1
            save_warns(warns)
            count = warns[key]
            await bot.send_message(chat.id, f"⚠️ {user.first_name}, links are not allowed! Warning {count}/{WARN_LIMIT}")
            if count >= WARN_LIMIT:
                await restrict_member(bot, chat.id, uid)
                await bot.send_message(chat.id, f"🔇 {user.first_name} has been muted after {WARN_LIMIT} warnings for links.")
            return

        # ABUSIVE detection
        text_to_check = (message.text or "") + " " + (message.caption or "")
        if contains_abusive_text(text_to_check):
            try:
                await message.delete()
            except Exception:
                pass
            key = make_key(chat.id, uid)
            warns[key] = warns.get(key, 0) + 1
            save_warns(warns)
            count = warns[key]
            await bot.send_message(chat.id, f"🚫 {user.first_name} used abusive language. Warning {count}/{WARN_LIMIT}")
            if count >= WARN_LIMIT:
                await restrict_member(bot, chat.id, uid)
                await bot.send_message(chat.id, f"🔇 {user.first_name} has been muted after {WARN_LIMIT} warnings for abusive language.")
            return

        # SPAM detection: consecutive messages only
        st = spam_track[chat.id]
        if st["last_user"] == uid:
            st["count"] += 1
        else:
            st["last_user"] = uid
            st["count"] = 1
        spam_track[chat.id] = st
        if st["count"] >= SPAM_THRESHOLD:
            await restrict_member(bot, chat.id, uid)
            await bot.send_message(chat.id, f"🚫 {user.first_name} has been muted for spamming ({SPAM_THRESHOLD} continuous messages).")
            spam_track[chat.id] = {"last_user": None, "count": 0}
            return

    @dp.message(content_types=types.ContentType.NEW_CHAT_MEMBERS)
    async def welcome(message: Message):
        for m in message.new_chat_members:
            await message.reply(f"👋 Welcome {m.first_name} to {message.chat.title}! Please be respectful and follow the group rules.")

    @dp.message(Command("admins"))
    async def cmd_admins(message: Message):
        admins = await message.chat.get_administrators()
        mentions = []
        for a in admins:
            u = a.user
            mentions.append(f"@{u.username}" if u.username else (u.first_name or str(u.id)))
        await message.reply("Admins: " + ", ".join(mentions))

    @dp.message(Command("mute"))
    async def cmd_mute(message: Message):
        admins = [int(a.user.id) for a in await message.chat.get_administrators()]
        if not (message.from_user.id in admin_ids or message.from_user.id in admins):
            return await message.reply("❌ Only admins can use this command.")
        if message.reply_to_message:
            target = message.reply_to_message.from_user.id
        else:
            parts = (message.text or "").split()
            if len(parts) < 2:
                return await message.reply("Usage: reply or /mute <user_id>")
            target = int(parts[1])
        await restrict_member(bot, message.chat.id, target)
        await message.reply("🔇 User muted.")

    @dp.message(Command("unmute"))
    async def cmd_unmute(message: Message):
        admins = [int(a.user.id) for a in await message.chat.get_administrators()]
        if not (message.from_user.id in admin_ids or message.from_user.id in admins):
            return await message.reply("❌ Only admins can use this command.")
        if message.reply_to_message:
            target = message.reply_to_message.from_user.id
        else:
            parts = (message.text or "").split()
            if len(parts) < 2:
                return await message.reply("Usage: reply or /unmute <user_id>")
            target = int(parts[1])
        await unrestrict_member(bot, message.chat.id, target)
        await message.reply("🔊 User unmuted.")

    @dp.message(Command("ban"))
    async def cmd_ban(message: Message):
        admins = [int(a.user.id) for a in await message.chat.get_administrators()]
        if not (message.from_user.id in admin_ids or message.from_user.id in admins):
            return await message.reply("❌ Only admins can use this command.")
        if message.reply_to_message:
            target = message.reply_to_message.from_user.id
        else:
            parts = (message.text or "").split()
            if len(parts) < 2:
                return await message.reply("Usage: reply or /ban <user_id>")
            target = int(parts[1])
        try:
            await bot.ban_chat_member(chat_id=message.chat.id, user_id=target)
            await message.reply("⛔ User banned.")
        except Exception as e:
            await message.reply(f"Failed to ban: {e}")

    @dp.message(Command("unban"))
    async def cmd_unban(message: Message):
        admins = [int(a.user.id) for a in await message.chat.get_administrators()]
        if not (message.from_user.id in admin_ids or message.from_user.id in admins):
            return await message.reply("❌ Only admins can use this command.")
        parts = (message.text or "").split()
        if len(parts) < 2:
            return await message.reply("Usage: /unban <user_id>")
        target = int(parts[1])
        try:
            await bot.unban_chat_member(chat_id=message.chat.id, user_id=target)
            await message.reply("✅ User unbanned.")
        except Exception as e:
            await message.reply(f"Failed to unban: {e}")

    @dp.message(Command("warn"))
    async def cmd_warn(message: Message):
        admins = [int(a.user.id) for a in await message.chat.get_administrators()]
        if not (message.from_user.id in admin_ids or message.from_user.id in admins):
            return await message.reply("❌ Only admins can use this command.")
        if message.reply_to_message:
            target = message.reply_to_message.from_user.id
        else:
            parts = (message.text or "").split()
            if len(parts) < 2:
                return await message.reply("Usage: reply or /warn <user_id>")
            target = int(parts[1])
        key = f"{message.chat.id}:{target}"
        warns[key] = warns.get(key, 0) + 1
        save_warns(warns)
        await message.reply(f"⚠️ User warned. ({warns[key]}/{WARN_LIMIT})")
        if warns[key] >= WARN_LIMIT:
            await restrict_member(bot, message.chat.id, target)
            await message.reply("🔇 User muted due to warnings.")

    @dp.message(Command("resetwarns"))
    async def cmd_resetwarns(message: Message):
        admins = [int(a.user.id) for a in await message.chat.get_administrators()]
        if not (message.from_user.id in admin_ids or message.from_user.id in admins):
            return await message.reply("❌ Only admins can use this command.")
        if message.reply_to_message:
            target = message.reply_to_message.from_user.id
        else:
            parts = (message.text or "").split()
            if len(parts) < 2:
                return await message.reply("Usage: reply or /resetwarns <user_id>")
            target = int(parts[1])
        key = f"{message.chat.id}:{target}"
        warns[key] = 0
        save_warns(warns)
        await message.reply("✅ Warnings reset.")

def cleanup_on_shutdown(dp: Dispatcher, bot: Bot):
    # placeholder for cleanup actions
    return asyncio.sleep(0)
