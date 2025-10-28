import re
import time
import logging
from collections import defaultdict
from typing import Dict
from aiogram import types, Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import ChatPermissions, Message

# ---------------- CONFIG ----------------
WARN_LIMIT = 3
SPAM_THRESHOLD = 5            # consecutive messages threshold
MUTE_DURATION_SECONDS = 60*60*24*365*10  # "permanent" ~10 years
ABUSIVE_FILE = "abusive_words.txt"

logging.basicConfig(level=logging.INFO)

# ---------------- STORAGE ----------------
try:
    with open(ABUSIVE_FILE, "r", encoding="utf-8") as f:
        ABUSIVE = set([line.strip().lower() for line in f if line.strip()])
except FileNotFoundError:
    sample = ["fuck","bitch","madarchod","behenchod","chutiya","bc","mc","randi","gaand","gandu","lund","lauda"] 
    with open(ABUSIVE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sample))
    ABUSIVE = set(sample)

# in-memory warns & spam trackers
warns: Dict[int, int] = defaultdict(int)  # key: user_id -> warn count (global per chat in messages)
# per-chat consecutive message tracker:
# { chat_id: {"last_user": user_id, "count": n} }
user_sequences: Dict[int, Dict] = defaultdict(lambda: {"last_user": None, "count": 0})

# ---------------- HELPERS ----------------
def mute_perms() -> ChatPermissions:
    return ChatPermissions(can_send_messages=False, can_send_media_messages=False,
                       can_send_other_messages=False, can_add_web_page_previews=False)

def unmute_perms() -> ChatPermissions:
    return ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                       can_send_other_messages=True, can_add_web_page_previews=True)

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.is_chat_admin() or member.is_chat_owner()
    except Exception:
        return False

def contains_link_in_message(msg: Message) -> bool:
    # check entities (url/text_link), caption, text and forwarded
    if getattr(msg, 'entities', None):
        for ent in msg.entities:
            if ent.type in ("url", "text_link"):
                return True
    if getattr(msg, 'caption', None) and ("http" in (msg.caption or "").lower() or "t.me" in (msg.caption or "").lower()):
        return True
    if getattr(msg, 'text', None) and ("http" in (msg.text or "").lower() or "t.me" in (msg.text or "").lower()):
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

def pretty_user(u: types.User) -> str:
    name = (u.first_name or "") + ( (" " + u.last_name) if u.last_name else "")
    if u.username:
        return f"{name} (@{u.username})"
    return name or str(u.id)

# ---------------- REGISTER HANDLERS ----------------
def register_handlers(dp: Dispatcher, bot: Bot):

    @dp.message()
    async def all_messages(message: Message):
        chat = message.chat
        if chat.type not in ("group", "supergroup"):
            return

        user = message.from_user
        uid = user.id

        # Admins bypass moderation
        if await is_admin(bot, chat.id, uid):
            # reset spam sequence if admin speaks (prevents accidental consecutive count)
            user_sequences[chat.id] = {"last_user": None, "count": 0}
            return

        # 1) Link detection (covers caption/forwarded)
        if contains_link_in_message(message):
            try:
                await message.delete()
            except Exception:
                pass
            warns[uid] += 1
            count = warns[uid]
            await bot.send_message(chat.id, f"⚠️ {pretty_user(user)}, links are not allowed! Warning {count}/{WARN_LIMIT}")
            if count >= WARN_LIMIT:
                try:
                    await bot.restrict_chat_member(chat.id, uid, permissions=mute_perms(), until_date=int(time.time())+MUTE_DURATION_SECONDS)
                    await bot.send_message(chat.id, f"🔇 {pretty_user(user)} has been muted after {WARN_LIMIT} warnings for links.")
                except Exception:
                    pass
            return

        # 2) Abusive word detection
        text_to_check = (message.text or "") + " " + (message.caption or "")
        if contains_abusive_text(text_to_check):
            try:
                await message.delete()
            except Exception:
                pass
            warns[uid] += 1
            count = warns[uid]
            await bot.send_message(chat.id, f"🚫 {pretty_user(user)} used abusive language. Warning {count}/{WARN_LIMIT}")
            if count >= WARN_LIMIT:
                try:
                    await bot.restrict_chat_member(chat.id, uid, permissions=mute_perms(), until_date=int(time.time())+MUTE_DURATION_SECONDS)
                    await bot.send_message(chat.id, f"🔇 {pretty_user(user)} has been muted after {WARN_LIMIT} warnings for abusive language.")
                except Exception:
                    pass
            return

        # 3) Spam detection: consecutive messages logic
        seq = user_sequences[chat.id]
        if seq["last_user"] == uid:
            seq["count"] += 1
        else:
            seq["last_user"] = uid
            seq["count"] = 1
        user_sequences[chat.id] = seq

        if seq["count"] >= SPAM_THRESHOLD:
            try:
                await bot.restrict_chat_member(chat.id, uid, permissions=mute_perms(), until_date=int(time.time())+MUTE_DURATION_SECONDS)
                await bot.send_message(chat.id, f"🚫 {pretty_user(user)} has been muted for spamming ({SPAM_THRESHOLD} continuous messages).")
            except Exception:
                pass
            # reset sequence
            user_sequences[chat.id] = {"last_user": None, "count": 0}
            return

    # Welcome new members (works for new chat members messages)
    @dp.message(content_types=types.ContentType.NEW_CHAT_MEMBERS)
    async def welcome(message: Message):
        for m in message.new_chat_members:
            await message.reply(f"👋 Welcome {m.first_name} to {message.chat.title}! Please be respectful and follow the group rules.")

    # ---------------- Admin commands (admin only) ----------------
    async def _is_admin_cmd(msg: Message) -> bool:
        return await is_admin(bot, msg.chat.id, msg.from_user.id)

    @dp.message(Command("mute"))
    async def cmd_mute(message: Message):
        if not await _is_admin_cmd(message):
            return await message.reply("❌ Only admins can use this command.")
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            target_name = message.reply_to_message.from_user.first_name
        else:
            parts = (message.text or "").split()
            if len(parts) < 2:
                return await message.reply("Usage: reply to user or /mute <user_id>")
            target_id = int(parts[1]); target_name = str(target_id)
        try:
            await bot.restrict_chat_member(message.chat.id, target_id, permissions=mute_perms(), until_date=int(time.time())+MUTE_DURATION_SECONDS)
            await message.reply(f"🔇 {target_name} has been muted by admin.")
        except Exception as e:
            await message.reply(f"Failed to mute: {e}")

    @dp.message(Command("unmute"))
    async def cmd_unmute(message: Message):
        if not await _is_admin_cmd(message):
            return await message.reply("❌ Only admins can use this command.")
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            target_name = message.reply_to_message.from_user.first_name
        else:
            parts = (message.text or "").split()
            if len(parts) < 2:
                return await message.reply("Usage: reply to user or /unmute <user_id>")
            target_id = int(parts[1]); target_name = str(target_id)
        try:
            await bot.restrict_chat_member(message.chat.id, target_id, permissions=unmute_perms())
            await message.reply(f"🔊 {target_name} has been unmuted by admin.")
        except Exception as e:
            await message.reply(f"Failed to unmute: {e}")

    @dp.message(Command("ban"))
    async def cmd_ban(message: Message):
        if not await _is_admin_cmd(message):
            return await message.reply("❌ Only admins can use this command.")
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            target_name = message.reply_to_message.from_user.first_name
        else:
            parts = (message.text or "").split()
            if len(parts) < 2:
                return await message.reply("Usage: reply to user or /ban <user_id>")
            target_id = int(parts[1]); target_name = str(target_id)
        try:
            await bot.ban_chat_member(message.chat.id, target_id)
            await message.reply(f"⛔ {target_name} has been banned by admin.")
        except Exception as e:
            await message.reply(f"Failed to ban: {e}")

    @dp.message(Command("unban"))
    async def cmd_unban(message: Message):
        if not await _is_admin_cmd(message):
            return await message.reply("❌ Only admins can use this command.")
        parts = (message.text or "").split()
        if len(parts) < 2:
            return await message.reply("Usage: /unban <user_id>")
        target_id = int(parts[1])
        try:
            await bot.unban_chat_member(message.chat.id, target_id)
            await message.reply(f"✅ User {target_id} has been unbanned by admin.")
        except Exception as e:
            await message.reply(f"Failed to unban: {e}")

    @dp.message(Command("warn"))
    async def cmd_warn(message: Message):
        if not await _is_admin_cmd(message):
            return await message.reply("❌ Only admins can use this command.")
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            target_name = message.reply_to_message.from_user.first_name
        else:
            parts = (message.text or "").split()
            if len(parts) < 2:
                return await message.reply("Usage: /warn <reply or user_id>")
            target_id = int(parts[1]); target_name = str(target_id)
        warns[target_id] += 1
        count = warns[target_id]
        await message.reply(f"⚠️ {target_name} warned ({count}/{WARN_LIMIT}).")
        if count >= WARN_LIMIT:
            try:
                await bot.restrict_chat_member(message.chat.id, target_id, permissions=mute_perms(), until_date=int(time.time())+MUTE_DURATION_SECONDS)
                await message.reply(f"🔇 {target_name} has been muted automatically after {WARN_LIMIT} warnings.")
            except Exception:
                pass

    @dp.message(Command("resetwarns"))
    async def cmd_resetwarns(message: Message):
        if not await _is_admin_cmd(message):
            return await message.reply("❌ Only admins can use this command.")
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            warns[target_id] = 0
            await message.reply("✅ Warnings reset.")
        else:
            await message.reply("Reply to user to reset warnings.")

    @dp.message(Command("admins"))
    async def cmd_admins(message: Message):
        admins = await bot.get_chat_administrators(message.chat.id)
        mentions = []
        for a in admins:
            u = a.user
            mentions.append(f"@{u.username}" if u.username else (u.first_name or str(u.id)))
        await message.reply("Admins: " + ", ".join(mentions))

    logging.info("Handlers registered.")
