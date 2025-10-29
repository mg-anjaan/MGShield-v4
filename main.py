import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ChatPermissions
from datetime import datetime, timedelta

# --- Configuration and Initialization ---
# Set up logging for better visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Fetch the token from the environment variable. 
# NOTE: The token must be correct in the Render Environment Variables for the bot to connect.
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable not set.")
    # In a real deployment, you might raise an error here to stop the service immediately.

# Initialize Bot and Dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Simple rate-limiting state (user_id: [timestamps])
message_timestamps = {}
RATE_LIMIT_COUNT = 5 # Max messages allowed
RATE_LIMIT_PERIOD = 5 # In seconds

# List of abusive words and keywords
ABUSIVE_WORDS = ["spam", "abuse", "scam", "fuck", "shit", "bitch"] # Add your actual words here

# --- Helper Functions ---

# Function to clear any stale connections gracefully
async def clear_old_sessions():
    """Clears any old polling/webhook sessions before starting a new one."""
    logger.info("🗑️ Ensuring old webhook/polling sessions are cleared...")
    try:
        # Using delete_webhook without any parameters is the safest way to clear old connections
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Connection cleared successfully (Attempt 1).")
    except Exception as e:
        # The bot might be Unauthorized if the token is wrong. This is the last safety net.
        logger.error(f"❌ Failed to clear old session: {e}")
        # We proceed anyway, but the Unauthorized error means connection will fail later.

async def restrict_user(chat_id: int, user_id: int, mute_duration_minutes: int):
    """Restricts a user for a given duration."""
    
    # Calculate the until_date (required parameter for mute)
    until_date = datetime.now() + timedelta(minutes=mute_duration_minutes)
    
    # Define the permissions (setting all to False effectively mutes the user)
    # The 'can_send_messages' permission will be set to True only after the 'until_date' expires.
    # For now, we set it to False to mute.
    permissions = ChatPermissions(
        can_send_messages=False,
        can_send_audios=False,
        can_send_documents=False,
        can_send_photos=False,
        can_send_videos=False,
        can_send_video_notes=False,
        can_send_voice_notes=False,
        can_send_other_messages=False,
        can_send_polls=False,
        can_add_web_page_previews=False,
        can_change_info=False,
        can_invite_users=False,
        can_pin_messages=False,
        can_manage_topics=False
    )
    
    try:
        await bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=permissions,
            until_date=until_date # This makes the restriction temporary (a mute)
        )
        logger.info(f"✅ User {user_id} restricted (muted) for {mute_duration_minutes} minutes in chat {chat_id}.")
        return True
    except Exception as e:
        # This exception is what you will see in Render logs if the bot lacks 'Restrict members' permission 
        # OR if it tries to mute an admin/owner.
        logger.error(f"❌ Failed to restrict user {user_id} in chat {chat_id}. Check bot admin 'Restrict members' permission, or if the user is an admin. Error: {e}")
        return False


# --- Message Handlers ---

@dp.message(Command("start"))
async def command_start_handler(message: types.Message):
    """Handles the /start command."""
    # This command is not working because the bot fails to use its 'Send Messages' permission.
    await message.answer("🤖 MGShield bot is running and ready to protect your group!")


@dp.message()
async def message_handler(message: types.Message):
    """Handles all incoming messages for moderation logic."""
    
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    text = message.text.lower() if message.text else ""
    
    is_spam_detected = False
    
    # 1. Anti-Spam (Rate Limiting) Check
    now = datetime.now()
    if user_id not in message_timestamps:
        message_timestamps[user_id] = []
    
    # Filter out timestamps older than the rate limit period
    message_timestamps[user_id] = [ts for ts in message_timestamps[user_id] if now - ts < timedelta(seconds=RATE_LIMIT_PERIOD)]
    message_timestamps[user_id].append(now)
    
    if len(message_timestamps[user_id]) > RATE_LIMIT_COUNT:
        # Spam detected: Mute user and set flag
        is_spam_detected = True
        logger.warning(f"🚨 Spam detected from user: {username} ({user_id}). Muting for 15 minutes.")
        
        # Mute the user for 15 minutes
        mute_successful = await restrict_user(chat_id, user_id, mute_duration_minutes=15)
        
        # Send notification (Requires 'Send Messages' permission)
        if mute_successful:
            try:
                await message.answer(
                    f"⚠️ **Spam Alert!** User @{username} has been muted for 15 minutes due to message flooding. Please slow down.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                # This exception is what you will see in Render logs if the bot lacks 'Send Messages' permission.
                logger.error(f"❌ Failed to send spam notification message. Check bot admin 'Send Messages' permission. Error: {e}")
        
        # Clear the message list to reset the counter immediately after action
        message_timestamps[user_id] = []


    # Check for direct links in the message text
    # This detects common prefixes for direct links.
    contains_link = any(link_pattern in text for link_pattern in ["http://", "https://", "www."])

    # 2. Anti-Forward and Direct Link Check
    # Check if the message is a forward OR contains a direct link
    if message.forward_from or message.forward_from_chat or contains_link:
        logger.info(f"🗑️ Deleting message from {username} (ID: {user_id}) - Link or Forwarded content detected.")
        
        try:
            await message.delete()
            # Send feedback message (Requires 'Send Messages' permission)
            try:
                await message.answer(f"🚫 Links and forwarded messages are not allowed in this group. User @{username}'s message was deleted.")
            except Exception as e:
                logger.error(f"❌ Failed to send anti-link/forward notification. Check bot admin 'Send Messages' permission. Error: {e}")
            
            # Mute the user for 5 minutes (Requires 'Restrict members' permission)
            await restrict_user(chat_id, user_id, mute_duration_minutes=5)
            return

        except Exception as e:
            logger.error(f"❌ Failed to delete link/forwarded message. Check bot admin 'Delete messages' permission. Error: {e}")
            return # Stop processing this message


    # 3. Abusive Word / Keyword Filter
    if any(word in text for word in ABUSIVE_WORDS):
        logger.info(f"🗑️ Deleting message from {username} (ID: {user_id}) - Abusive word detected: {text}")
        
        try:
            await message.delete()
            # Send feedback message (Requires 'Send Messages' permission)
            try:
                await message.answer(f"✋ **Warning!** User @{username}'s message was deleted due to inappropriate language. Please keep the chat respectful.")
            except Exception as e:
                logger.error(f"❌ Failed to send abusive word notification. Check bot admin 'Send Messages' permission. Error: {e}")
            
            # Mute the user for 10 minutes (Requires 'Restrict members' permission)
            await restrict_user(chat_id, user_id, mute_duration_minutes=10)
            return
            
        except Exception as e:
            logger.error(f"❌ Failed to delete abusive word message. Check bot admin 'Delete messages' permission. Error: {e}")
            return # Stop processing this message


# --- Main Execution ---
async def main():
    """Main function to start the bot."""
    if not BOT_TOKEN:
        logger.error("🚫 Cannot start bot: BOT_TOKEN is missing.")
        return

    logger.info("🚀 Bot is starting...")
    
    # 1. Clear stale sessions
    await clear_old_sessions()
    
    # 2. Start Long Polling
    logger.info("📡 Starting Long Polling...")
    # The bot will now fetch updates directly from Telegram in a long-running loop
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Fatal error during long polling: {e}")


if __name__ == "__main__":
    # Ensure the code can be terminated gracefully
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}")
