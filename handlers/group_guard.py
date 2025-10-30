from aiogram import Dispatcher
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import asyncio
import logging

from utils import delete_later # Assumes utils.py has is_admin

logger = logging.getLogger(__name__)

# --- FLOOD CONTROL CONSTANTS ---
RATE_LIMIT_COUNT = 5 # Max messages allowed
RATE_LIMIT_PERIOD = 5 # In seconds

async def restrict_user_and_notify(message: Message, duration_minutes: int, reason: str):
    """Helper to restrict user, delete their last message, and send a notification."""
    try:
        # Mute the user
        until_date = datetime.now() + timedelta(minutes=duration_minutes)
        await message.chat.restrict(
            message.from_user.id,
            permissions=types.ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        
        # Send warning and schedule deletion
        warn = await message.reply(f"🤖 **Action!** User muted for {duration_minutes} minutes due to {reason}.")
        await delete_later(warn, 10)
        
    except Exception as e:
        logger.error(f"❌ Failed to restrict user {message.from_user.id}: {e}")
    finally:
        # Delete the triggering message
        try:
            await message.delete()
        except Exception:
            pass

def setup_group_guard(dp: Dispatcher):
    """Registers a handler for flood control."""

    @dp.message()
    async def group_protection(message: Message, state: FSMContext):
        # Skip private chats, commands, and admins
        if message.chat.type not in ["group", "supergroup"]:
            return
        if message.text and message.text.startswith('/'):
            return
        # You should integrate is_admin(message.chat, message.from_user.id) check here if you import it

        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        key = f"{chat_id}:{user_id}:timestamps"

        # State will be Redis-backed (or Memory if REDIS_URL is missing)
        data = await state.storage.redis.lrange(key, 0, -1) if hasattr(state.storage, 'redis') else []
        timestamps = [float(ts) for ts in data]
        current_time = message.date.timestamp()

        # 1. Filter out stale timestamps (Older than RATE_LIMIT_PERIOD)
        # We need a new list only of valid timestamps within the period
        valid_timestamps = [ts for ts in timestamps if current_time - ts <= RATE_LIMIT_PERIOD]
        
        # 2. Add current timestamp
        valid_timestamps.append(current_time)

        # 3. Check for flood
        if len(valid_timestamps) > RATE_LIMIT_COUNT:
            # Action: Mute the user for 15 minutes
            await restrict_user_and_notify(message, 15, "message flooding")
            
            # Clear the list immediately after action to reset the counter
            await state.storage.redis.delete(key)
            return

        # 4. Save the updated list back to Redis/Storage
        if hasattr(state.storage, 'redis'):
            await state.storage.redis.delete(key) # Clear old list
            if valid_timestamps:
                # Store all timestamps and set expiration for cleanup
                await state.storage.redis.rpush(key, *[str(ts) for ts in valid_timestamps])
                await state.storage.redis.expire(key, RATE_LIMIT_PERIOD)
        # If using MemoryStorage, you'd manage the dict directly here.
        
        return # Allow the message to continue
