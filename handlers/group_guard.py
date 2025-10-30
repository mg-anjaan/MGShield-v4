import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Router, Bot, F
from aiogram.types import Message, ChatPermissions
from aiogram.fsm.context import FSMContext

# Import utilities
from utils import delete_later, is_admin

logger = logging.getLogger(__name__)

# --- FLOOD CONTROL CONSTANTS ---
RATE_LIMIT_COUNT = 5  # Max messages allowed
RATE_LIMIT_PERIOD = 5 # In seconds

router = Router()

async def restrict_user_and_notify(message: Message, duration_minutes: int, reason: str):
    """Helper to restrict user, delete their message, and send a notification."""
    try:
        until_date = datetime.now() + timedelta(minutes=duration_minutes)
        
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        
        warn = await message.reply(
            f"🤖 **Action!** User muted for {duration_minutes} minutes due to **{reason}**."
        )
        await message.delete() 
        await delete_later(warn, 10)
        
    except Exception as e:
        logger.error(f"❌ Failed to restrict user {message.from_user.id} in {message.chat.id}: {e}")

@router.message(F.text.as_()) 
async def flood_control_handler(message: Message, state: FSMContext, bot: Bot):
    """Handler for persistent flood control using Redis list operations."""

    # 1. Skip non-group chats, commands, bots, and admins
    if message.chat.type not in ["group", "supergroup"]:
        return
    if message.text and message.text.startswith('/'):
        return
    if message.from_user.is_bot:
        return
    if await is_admin(bot, message.chat.id, message.from_user.id):
        return

    user_id = str(message.from_user.id)
    chat_id = str(message.chat.id)
    key = f"flood_timestamps:{chat_id}:{user_id}"
    
    # Check if storage is RedisStorage (critical for persistent flood control)
    if not hasattr(state.storage, 'redis'):
        logger.warning(f"Flood control for {user_id} in {chat_id} skipped: Redis storage not found.")
        return

    redis = state.storage.redis
    current_time = datetime.now().timestamp()
    
    # 1. Add the current timestamp to the list
    await redis.rpush(key, current_time)
    
    # 2. Trim old timestamps: Remove any timestamps older than the limit period.
    # NOTE: This uses LTRIM to keep only the newest elements, but is complex to do correctly
    # with time-based filtering in Redis lists alone. 
    
    # A safer, more direct approach: fetch all, filter in Python, save back (as you initially had).
    # OPTIMIZED FILTERING: Fetch timestamps and filter by time in Python
    timestamps = [float(ts) for ts in await redis.lrange(key, 0, -1)]
    valid_timestamps = [ts for ts in timestamps if current_time - ts <= RATE_LIMIT_PERIOD]
    
    # 3. Check for flood
    if len(valid_timestamps) > RATE_LIMIT_COUNT:
        logger.info(f"🚨 FLOOD DETECTED: User {user_id} in {chat_id}. Count: {len(valid_timestamps)}")
        await restrict_user_and_notify(message, 15, "message flooding")
        await redis.delete(key) # Clear the list immediately after action
        return
    
    # 4. Save the updated list (Only the valid ones, including the one just added)
    await redis.delete(key) 
    if valid_timestamps:
        await redis.rpush(key, *[str(ts) for ts in valid_timestamps])
    
    # 5. Set expiration for automatic cleanup
    if valid_timestamps:
        await redis.expire(key, RATE_LIMIT_PERIOD)
    
# Registration function
def setup_group_guard(dp: Router):
    dp.include_router(router)
