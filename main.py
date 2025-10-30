import asyncio
import re
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

# --- aiogram 2.x Imports ---
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ChatPermissions, ChatMemberAdministrator, ChatMemberOwner
from aiogram.dispatcher.filters import Command
from aiogram.utils.exceptions import BadRequest as TelegramBadRequest

# --- Configuration & Setup ---

# Read the token from environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") 
WARNING_FILE = "warnings.json"

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set. Please set it securely.")

# Initialize Bot and Dispatcher (for aiogram 2.x)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# --- 1. Persistence Utility Functions ---

def load_warnings() -> Dict[str, int]:
    if not os.path.exists(WARNING_FILE):
        return {}
    with open(WARNING_FILE, 'r') as f:
        try:
            content = f.read()
            return json.loads(content) if content else {}
        except json.JSONDecodeError:
            return {}

def save_warnings(data: Dict[str, int]):
    try:
        with open(WARNING_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        print(f"Error saving warnings to file: {e}")

def get_warn_key(chat_id: int, user_id: int) -> str:
    return f"{chat_id}-{user_id}"

async def warn_user(chat_id: int, user_id: int) -> int:
    warnings_data = load_warnings()
    key = get_warn_key(chat_id, user_id)
    new_count = warnings_data.get(key, 0) + 1
    warnings_data[key] = new_count
    save_warnings(warnings_data)
    return new_count

def clear_warnings(chat_id: int, user_id: int):
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
        # Check instance type for admin/owner
        return isinstance(chat_member, (ChatMemberAdministrator, ChatMemberOwner))
    except Exception:
        return False

def parse_time(time_str: str) -> Optional[int]:
    if not time_str: return None
    match = re.match(r"(\d+)([mhd])", time_str.lower())
    if not match: return None

    value, unit = int(match.group(1)), match.group(2)
    seconds = 0
    if unit == 'm': seconds = value * 60
    elif unit == 'h': seconds = value * 3600
    elif unit == 'd': seconds = value * 86400
    
    return int((datetime.now() + timedelta(seconds=seconds)).timestamp())

def extract_target_user(message: Message) -> Optional[Tuple[int, Optional[str]]]:
    user_id = None
    time_arg = None
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        args = message.text.split()[1:]
        if args: time_arg = args[0]
    else:
        args = message.text.split()[1:]
        if not args: return None
        if args[0].isdigit():
            user_id = int(args[0])
        if len(args) > 1:
            time_arg = args[1]
    
    return (user_id, time_arg) if user_id else None

async def delete_later(message: Message, delay_seconds: int):
    await asyncio.sleep(delay_seconds)
    try:
        # Correct aiogram 2.x method using message.bot
        await message.bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

# --- 3. Command Handlers ---

@dp.message_handler(Command("start"))
async def cmd_start(message: Message):
    await message.reply("🤖 GroupGuardian active! Use /help for commands.")
    await delete_later(message, 10)

@dp.message_handler(Command("mute"))
async def cmd_mute(message: Message):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
        
    target = extract_target_user(message)
    if not target: return await message.reply("Usage: Reply to user OR /mute USER_ID TIME (e.g., 10m)")
    user_id, raw_time = target
    
    until_date_ts = parse_time(raw_time) or int((datetime.now() + timedelta(hours=1)).timestamp())

    if await is_admin(message.bot, message.chat.id, user_id):
        return await message.reply("⚠️ I cannot mute an admin.")
        
    try:
        # aiogram 2.x method
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id, user_id=user_id,
            can_send_messages=False, 
            until_date=until_date_ts 
        )
        await message.reply(f"🔇 User muted for a limited time.", parse_mode="Markdown")
    except Exception as e:
        await message.reply(f"❌ Failed to mute user: {e}")
    await delete_later(message, 10)

@dp.message_handler(Command("unmute"))
async def cmd_unmute(message: Message):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
        
    target = extract_target_user(message)
    if not target: return await message.reply("Usage: Reply to user OR /unmute USER_ID")
    user_id, _ = target
    
    try:
        # Restoring permissions for unmute (aiogram 2.x style)
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id, user_id=user_id,
            can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        await message.reply("🔊 User unmuted.")
    except Exception as e:
        await message.reply(f"❌ Failed to unmute user: {e}")
        
    await delete_later(message, 10)

@dp.message_handler(Command("ban"))
async def cmd_ban(message: Message):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
        
    target = extract_target_user(message)
    if not target: return await message.reply("Usage: Reply to user OR /ban USER_ID")
    user_id, _ = target
    
    if await is_admin(message.bot, message.chat.id, user_id):
        return await message.reply("⚠️ I cannot ban an admin.")
        
    try:
        # aiogram 2.x method for permanent ban
        await message.bot.kick_chat_member(chat_id=message.chat.id, user_id=user_id)
        clear_warnings(message.chat.id, user_id)
        await message.reply("⛔ User banned.")
    except Exception as e:
        await message.reply(f"❌ Failed to ban user: {e}")
        
    await delete_later(message, 10)

@dp.message_handler(Command("unban"))
async def cmd_unban(message: Message):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
        
    target = extract_target_user(message)
    if not target: return await message.reply("Usage: Reply to user OR /unban USER_ID")
    user_id, _ = target
    
    try:
        # In aiogram 2.x, unban requires calling restrict_chat_member
        await message.bot.restrict_chat_member(chat_id=message.chat.id, user_id=user_id)
        await message.reply("✅ User unbanned.")
    except Exception as e:
        await message.reply(f"❌ Failed to unban user: {e}")
        
    await delete_later(message, 10)

@dp.message_handler(Command("warn"))
async def cmd_warn(message: Message):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ You must be an admin to use this.")
        
    target = extract_target_user(message)
    if not target: return await message.reply("Usage: Reply to a user OR /warn USER_ID")
    user_id, _ = target
    
    if await is_admin(message.bot, message.chat.id, user_id):
        return await message.reply("⚠️ I cannot warn an admin.")
        
    try:
        warns = await warn_user(message.chat.id, user_id)
        
        if warns >= 3:
            # Kick logic: Temporary ban for 60 seconds
            kick_until = int((datetime.now() + timedelta(seconds=60)).timestamp())
            
            # 1. Ban/Kick
            await message.bot.kick_chat_member(chat_id=message.chat.id, user_id=user_id, until_date=kick_until)
            # 2. Immediately Unban to allow rejoin (aiogram 2.x uses restrict_chat_member)
            await message.bot.restrict_chat_member(chat_id=message.chat.id, user_id=user_id) 
            # 3. Clear warnings
            clear_warnings(message.chat.id, user_id)
            
            await message.reply(f"❗ User **kicked** after reaching the limit of **{warns}** warns.", parse_mode="Markdown")
            
        else:
            await message.reply(f"⚠️ User warned. Current warnings: **{warns}/3**.", parse_mode="Markdown")
            
    except TelegramBadRequest as e:
        await message.reply(f"❌ Failed to process command. Check bot permissions. Error: {e}")
    except Exception as e:
        await message.
