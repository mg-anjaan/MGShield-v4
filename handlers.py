import os
import json
import re
import time
from typing import Dict
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
    ContextTypes,
)

# --- Config via environment ---
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "7996780813").split(",") if x.strip()]
WARN_FILE = "warnings.json"
WARN_LIMIT = int(os.environ.get("WARN_LIMIT", "3"))
SPAM_THRESHOLD = int(os.environ.get("SPAM_THRESHOLD", "5"))  # continuous messages threshold

# Placeholder abusive words list — replace with your private list before deploying
BAD_WORDS = ["<replace_with_your_private_bad_words>"]

# Link regex (covers text and captions, basic)
LINK_RE = re.compile(r"https?://\S+|t\.me/\S+|telegram\.me/\S+|bit\.ly/\S+", flags=re.IGNORECASE)

# Spam tracker: per-chat tracking of consecutive messages
SPAM_TRACK: Dict[int, Dict] = {}

# --- Persistence helpers ---
def load_warns():
    try:
        with open(WARN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_warns(w):
    with open(WARN_FILE, "w", encoding="utf-8") as f:
        json.dump(w, f, indent=2)

# --- Helpers ---
def is_admin_user(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def contains_bad_word(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    for w in BAD_WORDS:
        if not w:
            continue
        if re.search(rf"\b{re.escape(w)}\b", t):
            return True
    return False

def contains_link(text: str) -> bool:
    if not text:
        return False
    return bool(LINK_RE.search(text))

def extract_text(msg):
    parts = []
    if getattr(msg, "text", None):
        parts.append(msg.text)
    if getattr(msg, "caption", None):
        parts.append(msg.caption)
    return " ".join([p for p in parts if p])

# --- Build application ---
def build_application(token: str):
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("tagadmins", cmd_tagadmins))
    app.add_handler(CommandHandler("mute", cmd_mute, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("unmute", cmd_unmute, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("ban", cmd_ban, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("unban", cmd_unban, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("warn", cmd_warn, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("resetwarns", cmd_resetwarns, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("tagadmins", cmd_tagadmins, filters=filters.ChatType.GROUPS))

    app.add_handler(ChatMemberHandler(welcome_new_members, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), message_router))

    return app

# --- Commands ---
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Group Protection Bot active. Admin-only commands available.")

async def cmd_tagadmins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    admins = await chat.get_administrators()
    mentions = []
    for a in admins:
        if a.user.username:
            mentions.append(f"@{a.user.username}")
        else:
            mentions.append(a.user.first_name)
    if mentions:
        await update.message.reply_text(" ".join(mentions))
    else:
        await update.message.reply_text("No admins found to tag.")

async def _is_command_admin(update: Update) -> bool:
    user = update.effective_user
    return user and user.id in ADMIN_IDS

def _extract_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.reply_to_message:
        return msg.reply_to_message.from_user
    if context.args:
        try:
            uid = int(context.args[0])
            # return a simple object-like container with id and first_name
            class U: pass
            u = U(); u.id = uid; u.first_name = str(uid)
            return u
        except:
            return None
    return None

async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _is_command_admin(update):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    target = _extract_target_user(update, context)
    if not target:
        await update.message.reply_text("Usage: reply to a user or /mute <user_id>")
        return
    try:
        await update.effective_chat.restrict_member(target.id, permissions=ChatPermissions(can_send_messages=False))
        await update.effective_chat.send_message(f"🔇 {target.first_name} has been muted by admin.")
    except Exception as e:
        await update.message.reply_text(f"Failed to mute: {e}")

async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _is_command_admin(update):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    target = _extract_target_user(update, context)
    if not target:
        await update.message.reply_text("Usage: reply to a user or /unmute <user_id>")
        return
    try:
        await update.effective_chat.restrict_member(target.id, permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        await update.effective_chat.send_message(f"🔊 {target.first_name} has been unmuted by admin.")
    except Exception as e:
        await update.message.reply_text(f"Failed to unmute: {e}")

async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _is_command_admin(update):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    target = _extract_target_user(update, context)
    if not target:
        await update.message.reply_text("Usage: reply to a user or /ban <user_id>")
        return
    try:
        await update.effective_chat.ban_member(target.id)
        await update.effective_chat.send_message(f"⛔ {target.first_name} has been banned by admin.")
    except Exception as e:
        await update.message.reply_text(f"Failed to ban: {e}")

async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _is_command_admin(update):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    try:
        uid = int(context.args[0])
        await update.effective_chat.unban_member(uid)
        await update.effective_chat.send_message(f"✅ User {uid} has been unbanned by admin.")
    except Exception as e:
        await update.message.reply_text(f"Failed to unban: {e}")

async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _is_command_admin(update):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    msg = update.message
    if msg.reply_to_message:
        target = msg.reply_to_message.from_user
        warns = load_warns()
        key = f"{msg.chat_id}:{target.id}"
        warns[key] = warns.get(key, 0) + 1
        save_warns(warns)
        count = warns[key]
        await update.effective_chat.send_message(f"⚠️ {target.first_name} warned ({count}/{WARN_LIMIT}).")
        if count >= WARN_LIMIT:
            await update.effective_chat.restrict_member(target.id, permissions=ChatPermissions(can_send_messages=False))
            await update.effective_chat.send_message(f"🔇 {target.first_name} muted automatically after {WARN_LIMIT} warnings.")
    else:
        await update.message.reply_text("Reply to a user to warn them.")

async def cmd_resetwarns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _is_command_admin(update):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    msg = update.message
    if msg.reply_to_message:
        target = msg.reply_to_message.from_user
        warns = load_warns()
        key = f"{msg.chat_id}:{target.id}"
        warns[key] = 0
        save_warns(warns)
        await update.effective_chat.send_message(f"✅ Warnings reset for {target.first_name}.")
    else:
        await update.message.reply_text("Reply to a user to reset warnings.")

# Welcome handler
async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cm = update.chat_member
        new = cm.new_chat_member.user
        chat = await context.bot.get_chat(cm.chat.id)
        text = f"👋 Welcome {new.first_name} to {chat.title}! Please be respectful and follow the rules."
        await context.bot.send_message(chat_id=cm.chat.id, text=text)
    except Exception:
        pass

# Message router
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    chat_id = msg.chat.id
    user = msg.from_user

    # ignore admins
    try:
        member = await msg.chat.get_member(user.id)
        if member.status in ("administrator", "creator"):
            return
    except Exception:
        pass

    # extract text and captions
    text_parts = []
    if getattr(msg, "text", None):
        text_parts.append(msg.text)
    if getattr(msg, "caption", None):
        text_parts.append(msg.caption)
    text = " ".join([p for p in text_parts if p]).strip()

    # Link check (covers captions and forwarded text)
    if contains_link(text):
        try:
            await msg.delete()
        except Exception:
            pass
        warns = load_warns()
        key = f"{chat_id}:{user.id}"
        warns[key] = warns.get(key, 0) + 1
        save_warns(warns)
        count = warns[key]
        await msg.chat.send_message(f"⚠️ {user.first_name}, links are not allowed! Warning {count}/{WARN_LIMIT}.")
        if count >= WARN_LIMIT:
            await msg.chat.restrict_member(user.id, permissions=ChatPermissions(can_send_messages=False))
            await msg.chat.send_message(f"🔇 {user.first_name} has been muted after {WARN_LIMIT} warnings for links.")
        return

    # Abusive check
    if contains_bad_word(text):
        try:
            await msg.delete()
        except Exception:
            pass
        warns = load_warns()
        key = f"{chat_id}:{user.id}"
        warns[key] = warns.get(key, 0) + 1
        save_warns(warns)
        count = warns[key]
        await msg.chat.send_message(f"🚫 {user.first_name} used abusive language. Warning {count}/{WARN_LIMIT}.")
        if count >= WARN_LIMIT:
            await msg.chat.restrict_member(user.id, permissions=ChatPermissions(can_send_messages=False))
            await msg.chat.send_message(f"🔇 {user.first_name} has been muted after {WARN_LIMIT} warnings for abusive language.")
        return

    # Spam detection: continuous messages from same user
    st = SPAM_TRACK.get(chat_id, {"last_sender": None, "count": 0, "last_time": 0})
    if st["last_sender"] == user.id:
        st["count"] += 1
    else:
        st["last_sender"] = user.id
        st["count"] = 1
    st["last_time"] = int(time.time())
    SPAM_TRACK[chat_id] = st

    if st["count"] >= SPAM_THRESHOLD:
        try:
            await msg.chat.restrict_member(user.id, permissions=ChatPermissions(can_send_messages=False))
            await msg.chat.send_message(f"🚫 {user.first_name} has been muted for spamming (continuous {SPAM_THRESHOLD} messages).")
        except Exception:
            pass
        SPAM_TRACK[chat_id] = {"last_sender": None, "count": 0, "last_time": 0}
        return

# helpers
async def _is_command_admin(update: Update):
    user = update.effective_user
    return user and user.id in ADMIN_IDS

def _extract_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.reply_to_message:
        return msg.reply_to_message.from_user
    if context.args:
        try:
            uid = int(context.args[0])
            class U: pass
            u = U(); u.id = uid; u.first_name = str(uid)
            return u
        except:
            return None
    return None
