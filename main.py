import asyncio
import re
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, ChatPermissions, ChatMemberAdministrator, ChatMemberOwner
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

# --- Configuration ---
BOT_TOKEN = "YOUR_BOT_TOKEN" 
WARNING_FILE = "warnings.json"

# Initialize the router
router = Router()

# --- 1. Persistence Utility Functions ---

def load_warnings() -> Dict[str, int]:
    """Loads warnings from the JSON file."""
    if not os.path.exists(WARNING_FILE):
        return {}
    with open(WARNING_FILE, 'r') as f:
        # Load keys as strings, then convert back to tuple keys later if needed
        # For simplicity in JSON, we will use a "chat_id-user_id" string key format.
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_warnings(data: Dict[str, int]):
    """Saves warnings to the JSON file."""
    with open(WARNING_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_warn_key(chat_id: int, user_id: int) -> str:
    """Creates a unique string key for the chat/user combination."""
    return f"{chat_id}-{user_id}"

async def warn_user(chat_id: int, user_id: int) -> int:
    """Increments a user's warning count, saves it, and returns the new count."""
    warnings_data = load_warnings()
    key = get_warn_key(chat_id, user_id)
    
    # Get current count, increment, and save
    current_count = warnings_data.get(key, 0)
    new_count = current_count + 1
    warnings_data[key] = new_count
    
    save_warnings(warnings_data)
    return new_count

def clear_warnings(chat_id: int, user_id: int):
    """Resets a user's warning count after a kick/ban."""
    warnings_data = load_warnings()
    key = get_warn_key(chat_id, user_id)
    if key in warnings_data:
        del warnings_data[key]
        save_warnings(warnings_data)

# --- 2. General Utility Functions ---

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Checks if a user is an administrator or owner of the chat."""
    try:
        chat_member = await bot.get_chat_member(chat_id, user_id)
        return isinstance(chat_member, (ChatMemberAdministrator, ChatMemberOwner))
    except Exception:
        return False

def parse_time(time_str: str) -> Optional[int]:
    """Parses time string (e.g., '10m', '1h') to Unix timestamp."""
    if not time_str:
        return None
    
    match = re.match(r"(\d+)([mhd])", time_str.lower())
    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2)
    
    # Calculate seconds
    seconds = 0
    if unit == 'm': seconds = value * 60
    elif unit == 'h': seconds = value * 3600
    elif unit == 'd': seconds = value * 86400

    # Return the target Unix timestamp
    return int((datetime.now() + timedelta(seconds=seconds)).timestamp())

def extract_target_user(message: Message) -> Optional[Tuple[int, Optional[str]]]:
    """
    Extracts target user ID from a reply or command arguments.
    Returns (user_id, raw_time_string)
    """
    user_id = None
    time_arg = None
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        args = message.text.split()[1:]
        if args: time_arg = args[0]
            
    else:
        args = message.text.split()[1:]
        if not args: return None
            
        target_str = args[0]
        if target_str.isdigit():
            user_id = int(target_str)
        
        if len(args) > 1:
            time_arg = args[1]
    
    return (user_id, time_arg) if user_id else None

async def delete_later(message: Message, delay_seconds: int):
    """Deletes the message after a delay."""
    await asyncio.sleep(delay_seconds)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

# --- 3. Command Handlers ---

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("🤖 GroupGuardian active! Use /help for commands.")
    await delete_later(message, 10)

@router.message(Command("mute"))
async def cmd_mute(message: Message):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
        
    target = extract_target_user(message)
    if not target:
        return await message.reply("Usage: Reply to user OR /mute USER_ID TIME (e.g., 10m)")
        
    user_id, raw_time = target
    until_date_ts = parse_time(raw_time)
    
    # Set default mute time to 1 hour if not provided or time not parsed
    if until_date_ts is None:
        until_date_ts = int((datetime.now() + timedelta(hours=1)).timestamp())

    if await is_admin(message.bot, message.chat.id, user_id):
        return await message.reply("⚠️ I cannot mute an admin.")
        
    try:
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False), 
            until_date=until_date_ts 
        )
        await message.reply(f"🔇 User `{user_id}` muted until {datetime.fromtimestamp(until_date_ts).strftime('%H:%M:%S')}.", parse_mode="Markdown")
    except Exception as e:
        await message.reply(f"❌ Failed to mute user: {e}")
        
    await delete_later(message, 10)

@router.message(Command("unmute"))
async def cmd_unmute(message: Message):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
        
    target = extract_target_user(message)
    if not target:
        return await message.reply("Usage: Reply to user OR /unmute USER_ID")
        
    user_id, _ = target
    
    try:
        # Restoring all standard permissions lifts the mute
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_audios=True, can_send_documents=True,
                can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
                can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
                can_add_web_page_previews=True, can_invite_users=True,
            )
        )
        await message.reply("🔊 User unmuted.")
    except Exception as e:
        await message.reply(f"❌ Failed to unmute user: {e}")
        
    await delete_later(message, 10)

@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
        
    target = extract_target_user(message)
    if not target:
        return await message.reply("Usage: Reply to user OR /ban USER_ID")
        
    user_id, _ = target
    
    if await is_admin(message.bot, message.chat.id, user_id):
        return await message.reply("⚠️ I cannot ban an admin.")
        
    try:
        await message.bot.ban_chat_member(chat_id=message.chat.id, user_id=user_id)
        clear_warnings(message.chat.id, user_id) # Clear warnings on ban
        await message.reply("⛔ User banned.")
    except Exception as e:
        await message.reply(f"❌ Failed to ban user: {e}")
        
    await delete_later(message, 10)

@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
        
    target = extract_target_user(message)
    if not target:
        return await message.reply("Usage: Reply to user OR /unban USER_ID")
        
    user_id, _ = target
    
    try:
        await message.bot.unban_chat_member(chat_id=message.chat.id, user_id=user_id)
        await message.reply("✅ User unbanned.")
    except Exception as e:
        await message.reply(f"❌ Failed to unban user: {e}")
        
    await delete_later(message, 10)

@router.message(Command("warn"))
async def cmd_warn(message: Message):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
        
    target = extract_target_user(message)
    if not target:
        return await message.reply("Usage: Reply to a user OR /warn USER_ID")
        
    user_id, _ = target
    
    if await is_admin(message.bot, message.chat.id, user_id):
        return await message.reply("⚠️ I cannot warn an admin.")
        
    try:
        # 1. Increment and get the new warns count (using persistent storage)
        warns = await warn_user(message.chat.id, user_id)
        
        # 2. Check the kick threshold
        if warns >= 3:
            # Action 1: Ban for 60 seconds (Soft Kick)
            kick_until = int((datetime.now() + timedelta(seconds=60)).timestamp())
            await message.bot.ban_chat_member(
                chat_id=message.chat.id, 
                user_id=user_id,
                until_date=kick_until
            )
            
            # Action 2: Immediately unban to allow the user to rejoin
            await message.bot.unban_chat_member(
                chat_id=message.chat.id,
                user_id=user_id,
                only_if_banned=True
            )
            
            # Action 3: Clear warnings after successful kick
            clear_warnings(message.chat.id, user_id)
            
            await message.reply(f"❗ User **kicked** after reaching the limit of **{warns}** warns.", parse_mode="Markdown")
            
        else:
            # Warning message
            await message.reply(f"⚠️ User warned. Current warnings: **{warns}/3**.", parse_mode="Markdown")
            
    except TelegramBadRequest as e:
        await message.reply(f"❌ Failed to kick user. Ensure the bot has **'Can ban users'** permission. Error: {e}")
    except Exception as e:
        await message.reply(f"❌ An unexpected error occurred: {e}")
        
    await delete_later(message, 10)

# --- Main Bot Setup and Execution ---

async def main():
    # Load warnings immediately at startup (optional, but good practice)
    # This prevents the first warn from overwriting data if the file already exists
    _ = load_warnings() 
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    print("Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
