import asyncio
import re
import sqlite3
from datetime import timedelta, datetime
from typing import Optional, Tuple, Dict, Any

from aiogram import Bot
from aiogram.types import Message, ChatMemberAdministrator, ChatMemberOwner, ChatPermissions
from aiogram.exceptions import TelegramBadRequest

# --- CONFIGURATION ---
DB_NAME = 'bot_data.db'
WARNING_THRESHOLD = 3
DEFAULT_WELCOME = "👋 Welcome to the group, {user_name}! Please read the rules."
ABUSIVE = {
    "fuck", "fucker", "motherfucker", "bitch", "bastard", "asshole", "slut", "whore", "porn", "nude", "sex", "horny",
    "madarchod", "behenchod", "bhosdike", "chutiya", "gandu", "lund", "randi", "gaand", "tatti", "kutte", "suar",
    "rakhail", "harami", "bsdk", "mc", "bc", "chod", "chodu", "lavde", "laude", "launde", "randwa", "randipana",
    "bhosdapan", "madarchodgiri", "bhenchodgiri", "ullu ke pathe", "ullu ka bacha", "maa ke lode", "behen ke laude"
}
_link_re = re.compile(r"https?://|t\.me/|telegram\.me/|\.\w{2,3}/", re.IGNORECASE)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            chat_id INTEGER PRIMARY KEY,
            welcome_msg TEXT
        )
    """)
    conn.commit()
    conn.close()

# --- ADMIN CHECK ---
async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ('administrator', 'creator')
    except Exception:
        return False

# --- FILTER CHECKS ---
def contains_link(message: Message) -> bool:
    text = (getattr(message, 'text', '') or '') + ' ' + (getattr(message, 'caption', '') or '')
    if bool(_link_re.search(text)): return True
    entities = message.entities or message.caption_entities
    if entities:
        for entity in entities:
            if entity.type in ('url', 'text_link'): return True
    return False

def is_forwarded(message: Message) -> bool:
    return getattr(message, 'forward_from', None) or getattr(message, 'forward_sender_name', None) or getattr(message, 'forward_from_chat', None)

def contains_abuse(message: Message) -> bool:
    text = (getattr(message, 'text', '') or '') + ' ' + (getattr(message, 'caption', '') or '')
    words = re.findall(r"[\w']+", text.lower())
    return any(w in ABUSIVE for w in words)

# --- DELETE MESSAGE LATER ---
async def delete_later(message: Message, delay: int = 10):
    try:
        await asyncio.sleep(delay)
        await message.delete()
    except Exception:
        pass

# --- WARN SYSTEM (PERSISTENT) ---
def _update_warning_db(chat_id: int, user_id: int, reset: bool = False) -> int:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if reset:
        cursor.execute("DELETE FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        conn.commit()
        conn.close()
        return 0

    cursor.execute("SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    result = cursor.fetchone()
    current_warns = result[0] if result else 0
    new_warns = current_warns + 1

    if result:
        cursor.execute("UPDATE warnings SET count = ? WHERE chat_id = ? AND user_id = ?", (new_warns, chat_id, user_id))
    else:
        cursor.execute("INSERT INTO warnings (chat_id, user_id, count) VALUES (?, ?, ?)", (chat_id, user_id, new_warns))

    conn.commit()
    conn.close()
    return new_warns

async def warn_user(chat_id: int, user_id: int, reset: bool = False) -> int:
    return await asyncio.to_thread(_update_warning_db, chat_id, user_id, reset)

async def get_warn_count(chat_id: int, user_id: int) -> int:
    def _get():
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    return await asyncio.to_thread(_get)

async def check_for_kick(message: Message, new_warns: int):
    if new_warns >= WARNING_THRESHOLD:
        user_id = message.from_user.id
        chat_id = message.chat.id
        bot = message.bot
        
        # Temporary ban for 1 minute to ensure kick
        kick_until = datetime.now() + timedelta(minutes=1)
        try:
            await bot.ban_chat_member(chat_id, user_id, until_date=kick_until)
            # Immediately unban to allow rejoin
            await bot.unban_chat_member(chat_id, user_id) 
            await warn_user(chat_id, user_id, reset=True)
            await message.answer(
                f"🚨 **{message.from_user.full_name}** was KICKED for reaching the warning limit ({WARNING_THRESHOLD} warns). Warnings reset.",
                parse_mode="Markdown"
            )
        except Exception as e:
            await message.answer(f"⚠️ KICK FAILED. Bot lacks permission or error: {e}")

# --- WELCOME MESSAGE UTILITIES ---
async def get_welcome_message(chat_id: int) -> str:
    def _get():
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT welcome_msg FROM settings WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else DEFAULT_WELCOME
    return await asyncio.to_thread(_get)

async def set_welcome_message(chat_id: int, message: str):
    def _set():
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO settings (chat_id, welcome_msg) VALUES (?, ?)",
            (chat_id, message)
        )
        conn.commit()
        conn.close()
    await asyncio.to_thread(_set)

# --- PARSE TIME AND EXTRACT USER ---
def parse_time(time_str: str) -> int:
    if not time_str or not time_str[-1].isalpha() or not time_str[:-1].isdigit():
        return 3600
    unit = time_str[-1].lower()
    value = int(time_str[:-1])
    if unit == 'm': return value * 60
    if unit == 'h': return value * 3600
    if unit == 'd': return value * 86400
    return 3600

def extract_target_user(message: Message) -> Optional[Tuple[int, int]]:
    parts = message.text.strip().split()
    target_user_id = None
    mute_time_seconds = 3600

    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
        if len(parts) > 1:
            mute_time_seconds = parse_time(parts[1])

    elif len(parts) >= 2:
        target_part = parts[1]
        if len(parts) > 2:
            mute_time_seconds = parse_time(parts[2])
        if target_part.isdigit():
            target_user_id = int(target_part)
        elif message.entities and message.entities[0].type == 'text_mention' and message.entities[0].user:
            target_user_id = message.entities[0].user.id
        else:
            return None 

    if target_user_id:
        return (target_user_id, int((datetime.now() + timedelta(seconds=mute_time_seconds)).timestamp()))
    return None
