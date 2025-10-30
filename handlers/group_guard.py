from aiogram import Dispatcher
from aiogram.types import Message, ChatPermissions
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import asyncio
import logging

from utils import delete_later # Assumes utils.py is in the parent directory

logger = logging.getLogger(__name__)

# --- FLOOD CONTROL CONSTANTS ---
RATE_LIMIT_COUNT = 5 # Max messages allowed
RATE_LIMIT_PERIOD = 5 # In seconds

async def restrict_user_and_notify(message: Message, duration_minutes: int, reason: str):
    """Helper to restrict user, delete their message, and send a notification."""
    try:
        # Mute the user
        until_date = datetime.now() + timedelta(minutes=duration_minutes)
        await message.chat.restrict(
            message.from_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        
        # Send warning and schedule deletion
        warn = await message.reply(f"🤖 **Action!** User muted for {duration_minutes} minutes due to **{reason}**.")
        await delete_later(warn, 10)
        
    except Exception as e:
        logger.error(f"❌ Failed to restrict user {message.from_user.id} in {message.chat.id}: {e}")
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
        # Skip private chats, commands, and admins (add is_admin check here if needed)
        if message.chat.type not in ["group", "supergroup"]:
            return
        if message.text and message.text.startswith('/'):
            return

        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        # Unique key for Redis/Storage: chat_id:user_id:timestamps
        key = f"{chat_id}:{user_id}:timestamps"

        # Check if storage is RedisStorage to access Redis methods
        if hasattr(state.storage, 'redis'):
            # Use Redis for persistent rate limiting
            redis = state.storage.redis
            current_time = message.date.timestamp()

            # 1. Trim old timestamps and get current count
            # This is complex in raw redis/memory but simplified by using a timestamp key

            # Use LTRIM to remove elements outside the rate limit window
            # Get all timestamps (as byte strings)
            data = await redis.lrange(key, 0, -1)
            
            # Convert to float and filter (less efficient than ZADD but simpler with RedisStorage)
            timestamps = [float(ts) for ts in data]
            valid_timestamps = [ts for ts in timestamps if current_time - ts <= RATE_LIMIT_PERIOD]
            
            # Add current timestamp
            valid_timestamps.append(current_time)

            # 2. Check for flood
            if len(valid_timestamps) > RATE_LIMIT_COUNT:
                # Action: Mute the user for 15 minutes
                await restrict_user_and_notify(message, 15, "message flooding")
                
                # Clear the list immediately after action
                await redis.delete(key)
                return

            # 3. Save the updated list back to Redis
            await redis.delete(key) # Clear old list
            if valid_timestamps:
                # Store all timestamps
                await redis.rpush(key, *[str(ts) for ts in valid_timestamps])
                # Set expiration for automatic cleanup
                await redis.expire(key, RATE_LIMIT_PERIOD)
        
        else:
            # Fallback to in-memory check (UNSTABLE on Railway)
            # This logic is complex with FSMContext and omitted here as Redis is required for stability.
            pass
            
        return # Allow the message to continue
