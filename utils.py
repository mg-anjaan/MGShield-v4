import re
import asyncio
from aiogram.types import Chat
from aiogram import Bot

# Basic link detection
_link_re = re.compile(r"https?://|t\.me/|telegram\.me/|\.\w{2,3}/", re.IGNORECASE)

# Example abusive words list (expand with Hindi + English slang)
ABUSIVE = {"badword","chut","bhosd","examplebad"}  # replace with your comprehensive list

async def is_admin(chat: Chat, user_id: int) -> bool:
    try:
        member = await chat.get_member(user_id)
        # Member methods differ by aiogram version; this is a best-effort check
        return getattr(member, 'is_chat_admin', lambda: getattr(member, 'status', '') in ('administrator','creator'))()
    except Exception:
        return False

def contains_link(message) -> bool:
    text = (getattr(message, 'text', '') or '') + ' ' + (getattr(message, 'caption', '') or '')
    return bool(_link_re.search(text))

def is_forwarded(message) -> bool:
    return getattr(message, 'forward_from', None) is not None or getattr(message, 'forward_sender_name', None) is not None

def contains_abuse(message) -> bool:
    text = (getattr(message, 'text', '') or '') + ' ' + (getattr(message, 'caption', '') or '')
    words = re.findall(r"[\w']+", text.lower())
    return any(w in ABUSIVE for w in words)

async def delete_later(message, delay: int = 10):
    try:
        await asyncio.sleep(delay)
        await message.delete()
    except Exception:
        pass

# Simple warn storage (in-memory)
_warns = {}
async def warn_user(chat_id: int, user_id: int) -> int:
    key = f"{chat_id}:{user_id}"
    _warns[key] = _warns.get(key, 0) + 1
    return _warns[key]

async def admins_list(chat: Chat):
    try:
        res = await chat.get_administrators()
        # return list of "FirstName" or "id"
        return [f"{m.user.first_name or m.user.id}:{m.user.id}" for m in res]
    except Exception:
        return []
