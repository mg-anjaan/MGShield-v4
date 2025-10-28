import os
import json
import logging
from typing import List
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# --- Config ---
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))  # set to your Telegram ID
WARN_FILE = "warnings.json"
WELCOME_FILE = "welcome.json"

# Abusive words list (add more Hindi slurs here)
BAD_WORDS = [
    "bhosdike","madarchod","chod","lund","randi","mc","bc","chutiya","fucker","fuck",
    "bsdk","gaand","kutte","harami","kamina","rakhail","suar","chud","gandu",
    "tatti","kutiya","betichod","behenchod","loda","chodna","lauda",
    "chut","gand","lodu","bhenkelode","madarchkd","randi","chutiyta"
]

LINK_KEYWORDS = ["t.me", "http://", "https://", "telegram.me", "bit.ly"]

# --- Helpers ---
def load_json_file(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

def save_json_file(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# --- Core handlers ---
def build_application(token: str):
    app = ApplicationBuilder().token(token).build()

    # commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ban", ban, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("unban", unban, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("mute", mute, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("unmute", unmute, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("warn", warn_cmd, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("setwelcome", set_welcome, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("delwelcome", del_welcome, filters=filters.ChatType.GROUPS))

    # new members welcome
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))

    # text messages detection
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), check_message))

    return app

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot active. Group protection enabled. Admin-only commands available.")

# Admin-only decorator
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            return
        if user.id != ADMIN_ID:
            await update.message.reply_text("❌ Only the admin can use this command.")
            return
        return await func(update, context)
    return wrapper

# Ban command: usage /ban (reply) or /ban <user_id>
@admin_only
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    target_id = None
    if msg.reply_to_message:
        target_id = msg.reply_to_message.from_user.id
        target_name = msg.reply_to_message.from_user.first_name
    elif context.args:
        try:
            target_id = int(context.args[0])
            target_name = str(context.args[0])
        except:
            await msg.reply_text("Usage: /ban (reply to a user) or /ban <user_id>")
            return
    if not target_id:
        await msg.reply_text("No target found. Reply to a user's message or provide their ID.")
        return
    try:
        await context.bot.ban_chat_member(chat_id=msg.chat_id, user_id=target_id)
        await msg.reply_text(f"🚫 {target_name} has been banned by admin.")
    except Exception as e:
        await msg.reply_text(f"Failed to ban: {e}")

@admin_only
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if context.args:
        try:
            uid = int(context.args[0])
            await context.bot.unban_chat_member(chat_id=msg.chat_id, user_id=uid)
            await msg.reply_text(f"✅ User {uid} unbanned.")
        except Exception as e:
            await msg.reply_text(f"Failed to unban: {e}")
    else:
        await msg.reply_text("Usage: /unban <user_id>")

@admin_only
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.reply_to_message:
        target = msg.reply_to_message.from_user
        await msg.chat.restrict_member(target.id, permissions=ChatPermissions(can_send_messages=False))
        await msg.reply_text(f"🔇 {target.first_name} muted.")
    else:
        await msg.reply_text("Reply to a user to mute them.")

@admin_only
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.reply_to_message:
        target = msg.reply_to_message.from_user
        await msg.chat.restrict_member(target.id, permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        await msg.reply_text(f"🔊 {target.first_name} unmuted.")
    else:
        await msg.reply_text("Reply to a user to unmute them.")

@admin_only
async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.reply_to_message:
        target = msg.reply_to_message.from_user
        warns = load_json_file(WARN_FILE, {})
        key = f"{msg.chat_id}:{target.id}"
        warns[key] = warns.get(key, 0) + 1
        save_json_file(WARN_FILE, warns)
        await msg.reply_text(f"⚠️ {target.first_name} warned ({warns[key]} / 3).")
        if warns[key] >= 3:
            await msg.chat.restrict_member(target.id, permissions=ChatPermissions(can_send_messages=False))
            await msg.reply_text(f"🔇 {target.first_name} muted automatically after 3 warnings.")
    else:
        await msg.reply_text("Reply to a user to warn them.")

@admin_only
async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if context.args:
        text = " ".join(context.args)
        welcomes = load_json_file(WELCOME_FILE, {})
        welcomes[str(msg.chat_id)] = text
        save_json_file(WELCOME_FILE, welcomes)
        await msg.reply_text("✅ Welcome message set.")
    else:
        await msg.reply_text("Usage: /setwelcome Your welcome message here. Use {first_name} to include the name.")

@admin_only
async def del_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    welcomes = load_json_file(WELCOME_FILE, {})
    if str(msg.chat_id) in welcomes:
        del welcomes[str(msg.chat_id)]
        save_json_file(WELCOME_FILE, welcomes)
        await msg.reply_text("✅ Welcome message removed.")
    else:
        await msg.reply_text("No welcome message set for this chat.")

async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    welcomes = load_json_file(WELCOME_FILE, {})
    text = welcomes.get(str(msg.chat_id), "Welcome {first_name}!")
    for member in msg.new_chat_members:
        await msg.reply_text(text.format(first_name=member.first_name))

# message checks for abuse and links
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    text = msg.text.lower()

    # ignore admins
    member = await msg.chat.get_member(msg.from_user.id)
    if member.status in ("administrator", "creator"):
        return

    # link detection - delete and notify admin
    if any(k in text for k in LINK_KEYWORDS):
        try:
            await msg.delete()
            await msg.chat.send_message(f"⚠️ Link removed from {msg.from_user.first_name}. Only admins may post links.")
            logging.info("Deleted link message from %s in %s", msg.from_user.id, msg.chat_id)
        except Exception as e:
            logging.error("Failed to delete link: %s", e)
        return

    # abusive words detection
    if any(bad in text for bad in BAD_WORDS):
        # increment warning count and mute if >=3
        warns = load_json_file(WARN_FILE, {})
        key = f"{msg.chat_id}:{msg.from_user.id}"
        warns[key] = warns.get(key, 0) + 1
        save_json_file(WARN_FILE, warns)
        count = warns[key]
        await msg.delete()
        await msg.chat.send_message(f"🚫 {msg.from_user.first_name} used abusive language and was warned ({count}/3).")
        logging.info("Warned %s (%s/%s)", msg.from_user.id, count, 3)
        if count >= 3:
            await msg.chat.restrict_member(msg.from_user.id, permissions=ChatPermissions(can_send_messages=False))
            await msg.chat.send_message(f"🔇 {msg.from_user.first_name} muted after 3 warnings.")
