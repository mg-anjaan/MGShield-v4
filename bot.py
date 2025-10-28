import os
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8383391764:AAFm0-a1tYbrwGdRwoKLzTqPVz48xH_mNC4"
ADMIN_ID = 7996780813
BAD_WORDS = [
    "bhosdike", "madarchod", "chod", "lund", "randi", "mc", "bc", "chutiya", "fucker",
    "fuck", "bsdk", "gaand", "kutte", "harami", "kamina", "rakhail", "suar",
    "chud", "gandu", "tatti", "kutiya", "betichod", "behenchod", "loda",
    "chodna", "lauda", "chut", "lodu", "bhenkelode", "madarchkd", "randi", "chutiyta"
]
LINK_KEYWORDS = ["t.me", "http", "https", "telegram.me", "bit.ly"]
WARNINGS = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    member = await update.effective_chat.get_member(user.id)
    if not member.status in ("administrator", "creator"):
        await update.message.reply_text("⚠️ Only admins can use this command.")
        return
    await update.message.reply_text("🤖 Bot is active and monitoring the group!")

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(
            f"👋 Welcome {member.first_name} to the group!\nPlease maintain respect and avoid using bad words or links."
        )

async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    text = message.text.lower()
    user = message.from_user
    member = await message.chat.get_member(user.id)
    if member.status in ("administrator", "creator"):
        return

    if any(word in text for word in BAD_WORDS):
        try:
            await message.chat.restrict_member(user.id, ChatPermissions(can_send_messages=False))
            await message.reply_text(f"🚫 {user.first_name} has been permanently muted for abusive language.")
            await context.bot.send_message(ADMIN_ID, f"⚠️ User muted:\n👤 {user.full_name}\n🆔 ID: {user.id}\n🗨️ Message: {message.text}")
        except Exception as e:
            await message.reply_text(f"⚠️ Could not mute user: {e}")
        return

    if any(link in text for link in LINK_KEYWORDS):
        try:
            await message.delete()
            WARNINGS[user.id] = WARNINGS.get(user.id, 0) + 1
            count = WARNINGS[user.id]
            if count >= 3:
                await message.chat.ban_member(user.id)
                await message.chat.send_message(f"🚨 {user.first_name} was banned after 3 warnings for sharing links.")
                WARNINGS.pop(user.id, None)
            else:
                await message.chat.send_message(f"⚠️ {user.first_name}, posting links is not allowed! Warning {count}/3.")
            await context.bot.send_message(ADMIN_ID, f"🔗 Link deleted:\n👤 {user.full_name}\nWarns: {count}\n🗨️ Message: {message.text}")
        except Exception as e:
            print("Error deleting link message:", e)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))
    app.run_polling()

if __name__ == "__main__":
    main()
