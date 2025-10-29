import re
import asyncio
from datetime import timedelta, datetime
from aiogram.types import Chat
from aiogram import Bot

# --- REGEX ---
_link_re = re.compile(r"https?://|t\.me/|telegram\.me/|\.\w{2,3}/", re.IGNORECASE)

# --- ABUSIVE WORDS (ENGLISH + HINDI/HINGLISH) ---
ABUSIVE = {
    "fuck", "fucker", "motherfucker", "bitch", "bastard", "asshole", "slut", "whore", "porn", "nude", "sex", "horny",
    "madarchod", "behenchod", "bhosdike", "chutiya", "gandu", "lund", "randi", "gaand", "tatti", "kutte", "suar",
    "rakhail", "harami", "bsdk", "mc", "bc", "chod", "chodu", "lavde", "laude", "launde", "randwa", "randipana",
    "bhosdapan", "madarchodgiri", "bhenchodgiri", "ullu ke pathe", "ullu ka bacha", "maa ke lode", "behen ke laude"
}

# --- ADMIN CHECK ---
async def is_admin(chat: Chat, user_id: int) -> bool:
    try:
        member = await chat.get_member(user_id)
        return member.status in ('administrator', 'creator')
    except Exception:
        return False

# --- LINK CHECK ---
def contains_link(message) -> bool:
    text = (getattr(message, 'text', '') or '') + ' ' + (getattr(message, 'caption', '') or '')
    return bool(_link_re.search(text))

# --- FORWARD CHECK ---
def is_forwarded(message) -> bool:
    return getattr(message, 'forward_from', None) or getattr(message, 'forward_sender_name', None)

# --- ABUSIVE CHECK ---
def contains_abuse(message) -> bool:
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

# --- WARN SYSTEM ---
_warns = {}
async def warn_user(chat_id: int, user_id: int) -> int:
    key = f"{chat_id}:{user_id}"
    _warns[key] = _warns.get(key, 0) + 1
    return _warns[key]

# --- ADMINS LIST ---
async def admins_list(chat: Chat):
    try:
        res = await chat.get_administrators()
        return [f"{m.user.first_name or m.user.id}:{m.user.id}" for m in res]
    except Exception:
        return []

# --- PARSE MUTE TIME STRING (e.g. '10m', '2h', '1d') ---
def parse_time(time_str: str) -> int:
    if not time_str:
        return 60  # default 1 minute
    unit = time_str[-1].lower()
    value = int(time_str[:-1]) if time_str[:-1].isdigit() else 1
    if unit == 'm':
        return value * 60
    if unit == 'h':
        return value * 3600
    if unit == 'd':
        return value * 86400
    return 60

# --- EXTRACT TARGET USER (for /mute /ban /warn /unmute etc.) ---
def extract_target_user(message):
    """
    Extract (user_id, until_date) from reply or command text.
    Usage: /mute @username 10m  OR  /ban 12345
    """
    # If command is a reply
    if message.reply_to_message:
        target = message.reply_to_message.from_user.id
        parts = message.text.strip().split()
        mute_time = parse_time(parts[1]) if len(parts) > 1 else 60
        return (target, datetime.utcnow() + timedelta(seconds=mute_time))

    # Parse text command
    parts = message.text.strip().split()
    if len(parts) < 2:
        return None
    user_part = parts[1]
    mute_time = parse_time(parts[2]) if len(parts) > 2 else 60
    user_id = None

    # Handle numeric ID or @username
    if user_part.isdigit():
        user_id = int(user_part)
    elif user_part.startswith("@"):
        user_id = user_part  # username (handled by Telegram)
    else:
        return None

    return (user_id, datetime.utcnow() + timedelta(seconds=mute_time))

