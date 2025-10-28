import os
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ChatMemberHandler, filters, ContextTypes
from telegram.constants import ChatType

ADMIN_ID = 7996780813
BAD_WORDS = [
    "bhosdike", "madarchod", "chod", "lund", "randi", "mc", "bc", "chutiya", "fucker", "fuck",
    "bsdk", "gaand", "kutte", "harami", "kamina", "rakhail", "suar", "chud", "gandu",
    "tatti", "kutiya", "betichod", "behenchod", "loda", "chodna", "lauda",
    "chut", "gand", "lodu", "bhenkelode", "madarchkd", "randi", "chutiyta"
]
LINK_KEYWORDS = ["t.me", "http", "https", "telegram.me", "bit.ly"]

warn_count = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot activated! Protecting this group from spam, links, and abusive words.")

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.chat_member.new_chat_members:
        await update.effective_chat.send_message(f"👋 Welcome {member.first_name}! Please follow group rules.")

def is_admin(member):
    return member.status in ["administrator", "creator"]

async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or message.chat.type != ChatType.SUPERGROUP:
        return

    user = message.from_user
    text = message.text.lower()

    # Skip admins
    member = await message.chat.get_member(user.id)
    if is_admin(member):
        return

    # Abusive word detection
    if any(word in text for word in BAD_WORDS):
        user_warns = warn_count.get(user.id, 0) + 1
        warn_count[user.id] = user_warns

        if user_warns >= 3:
            await message.chat.restrict_member(user.id, ChatPermissions(can_send_messages=False))
            await message.reply_text(f"🚫 {user.first_name} has been permanently muted for repeated abusive behavior.")
            warn_count[user.id] = 0
        else:
            await message.reply_text(f"⚠️ {user.first_name}, warning {user_warns}/3 for abusive language.")
        return

    # Link detection
    if any(link in text for link in LINK_KEYWORDS):
        try:
            await message.delete()
            await message.chat.send_message(f"⚠️ {user.first_name}, posting links is not allowed!")
        except:
            pass

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE, action):
    message = update.message
    member = await message.chat.get_member(update.effective_user.id)
    if not is_admin(member):
        await message.reply_text("❌ Only admins can use this command.")
        return

    if not context.args:
        await message.reply_text("⚠️ Please mention a user or provide their ID.")
        return

    try:
        user_id = int(context.args[0])
        if action == "mute":
            await message.chat.restrict_member(user_id, ChatPermissions(can_send_messages=False))
            await message.reply_text(f"🔇 User {user_id} has been muted.")
        elif action == "unmute":
            await message.chat.restrict_member(user_id, ChatPermissions(can_send_messages=True))
            await message.reply_text(f"🔈 User {user_id} has been unmuted.")
        elif action == "ban":
            await message.chat.ban_member(user_id)
            await message.reply_text(f"⛔ User {user_id} has been banned.")
        elif action == "unban":
            await message.chat.unban_member(user_id)
            await message.reply_text(f"✅ User {user_id} has been unbanned.")
        elif action == "warn":
            warn_count[user_id] = warn_count.get(user_id, 0) + 1
            await message.reply_text(f"⚠️ Warning issued to {user_id}. Total warnings: {warn_count[user_id]}")
        elif action == "resetwarns":
            warn_count[user_id] = 0
            await message.reply_text(f"✅ Warnings reset for {user_id}.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ BOT_TOKEN not found in environment variables.")
        return

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))

    for cmd in ["mute", "unmute", "ban", "unban", "warn", "resetwarns"]:
        app.add_handler(CommandHandler(cmd, lambda u, c, a=cmd: admin_command(u, c, a)))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
