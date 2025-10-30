import re
import asyncio
import sqlite3
from datetime import timedelta, datetime
from aiogram.types import Chat, Message
from aiogram import Bot

# --- CONFIGURATION ---
DB_NAME = 'bot_data.db' 

# The vast ABUSIVE set remains in place but is omitted for brevity here.
ABUSIVE = {
     "fuck", "fucker", "motherfucker", "bitch", "bastard", "asshole", "slut", "whore", "porn", "nude", "sex", "horny",
     "madarchod", "behenchod", "bhosdike", "chutiya", "gandu", "lund", "randi", "gaand", "tatti", "kutte", "suar",
     "rakhail", "harami", "bsdk", "mc", "bc", "chod", "chodu", "lavde", "laude", "launde", "randwa", "randipana",
     "bhosdapan", "madarchodgiri", "bhenchodgiri", "ullu ke pathe", "ullu ka bacha", "maa ke lode", "behen ke laude"
}

# --- REGEX ---
_link_re = re.compile(r"https?://|t\.me/|telegram\.me/|\.\w{2,3}/", re.IGNORECASE)

# --- DATABASE SETUP ---
def init_db():
    """Initializes the SQLite database and creates necessary tables."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 1. Warnings Table (for persistent user warnings)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )
    """)
    # 2. Settings Table (for custom welcome messages, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            chat_id INTEGER PRIMARY KEY,
            welcome_msg TEXT
        )
    """)
    conn.commit()
    conn.close()

# --- ADMIN CHECK ---
async def is_admin(chat: Chat, user_id: int) -> bool:
    try:
        # Use message.chat.get_member(user_id) if called from a Message handler
        member = await chat.get_member(user_id)
        return member.status in ('administrator', 'creator')
    except Exception:
        return False

# --- LINK CHECK (FIXED for Entities and Forwarded Links) ---
def contains_link(message: Message) -> bool:
    text = (getattr(message, 'text', '') or '') + ' ' + (getattr(message, 'caption', '') or '')

    # 1. Check for basic link patterns in text
    if bool(_link_re.search(text)):
        return True

    # 2. Check message entities (for embedded links)
    entities = message.entities or message.caption_entities
    if entities:
        for entity in entities:
            # Check for explicitly formatted links (URL or clickable text)
            if entity.type in ('url', 'text_link'):
                return True
                
    return False

# --- FORWARD CHECK ---
def is_forwarded(message: Message) -> bool:
    return getattr(message, 'forward_from', None) or getattr(message, 'forward_sender_name', None)

# --- ABUSIVE CHECK ---
def contains_abuse(message: Message) -> bool:
    text = (getattr(message, 'text', '') or '') + ' ' + (getattr(message, 'caption', '') or '')
    words = re.findall(r"[\w']+", text.lower())
    return any(w in ABUSIVE for w in words)

# --- DELETE MESSAGE LATER ---
async def delete_later(message, delay: int = 10):
    try:
        await asyncio.sleep(delay)
        await message.delete()
    except Exception:
        pass

# --- WARN SYSTEM (PERSISTENT FIX) ---
def _update_warning_db(chat_id: int, user_id: int) -> int:
    """Synchronous database operation for updating warnings."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?",
        (chat_id, user_id)
    )
    result = cursor.fetchone()
    current_warns = result[0] if result else 0
    new_warns = current_warns + 1

    if result:
        cursor.execute(
            "UPDATE warnings SET count = ? WHERE chat_id = ? AND user_id = ?",
            (new_warns, chat_id, user_id)
        )
    else:
        cursor.execute(
            "INSERT INTO warnings (chat_id, user_id, count) VALUES (?, ?, ?)",
            (chat_id, user_id, new_warns)
        )

    conn.commit()
    conn.close()
    return new_warns

async def warn_user(chat_id: int, user_id: int) -> int:
    """Runs the blocking database update asynchronously."""
    return await asyncio.to_thread(_update_warning_db, chat_id, user_id)

# --- WELCOME MESSAGE UTILITIES ---
def _get_welcome_db(chat_id: int) -> str:
    """Synchronous database operation to fetch welcome message."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT welcome_msg FROM settings WHERE chat_id = ?", (chat_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "👋 Welcome {user_name}! Please read the rules."

async def get_welcome_message(chat_id: int) -> str:
    return await asyncio.to_thread(_get_welcome_db, chat_id)

def _set_welcome_db(chat_id: int, message: str):
    """Synchronous database operation to set welcome message."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (chat_id, welcome_msg) VALUES (?, ?)",
        (chat_id, message)
    )
    conn.commit()
    conn.close()

async def set_welcome_message(chat_id: int, message: str):
    await asyncio.to_thread(_set_welcome_db, chat_id, message)


# --- PARSE MUTE TIME STRING (e.g. '10m', '2h', '1d') ---
def parse_time(time_str: str) -> int:
    # ... (Your existing correct parse_time function remains)
    if not time_str:
        return 60
    unit = time_str[-1].lower()
    value = int(time_str[:-1]) if time_str[:-1].isdigit() else 1
    if unit == 'm':
        return value * 60
    if unit == 'h':
        return value * 3600
    if unit == 'd':
        return value * 86400
    return 60

# --- EXTRACT TARGET USER (FIXED for Reliability) ---
def extract_target_user(message):
    """
    Extract (user_id, until_date_seconds) from reply or command text.
    Returns (user_id: int, seconds: int) or None.
    """
    parts = message.text.strip().split()
    
    target_user_id = None
    mute_time_seconds = 60 # Default to 1 minute

    # 1. Handle Reply
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
        # Mute time is the argument after the command (parts[1], if present)
        if len(parts) > 1:
            mute_time_seconds = parse_time(parts[1])

    # 2. Handle Text Command
    elif len(parts) >= 2:
        target_part = parts[1]
        if len(parts) > 2:
            mute_time_seconds = parse_time(parts[2])

        # A. Numeric ID (Most reliable)
        if target_part.isdigit():
            target_user_id = int(target_part)
        
        # B. Mention Entity (Less reliable, but we'll try to extract the user ID)
        elif message.entities and message.entities[0].type == 'text_mention' and message.entities[0].user:
            target_user_id = message.entities[0].user.id
        
        # C. Username String (@user) - Can't be used directly for restrict/ban without lookup, so we return None to force reply/ID.
        else:
            return None 

    if target_user_id:
        return (target_user_id, mute_time_seconds)
    return None
