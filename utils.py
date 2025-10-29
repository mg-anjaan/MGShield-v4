import re
import asyncio
from aiogram.types import Chat
from aiogram import Bot

# Basic link detection
_link_re = re.compile(r"https?://|t\.me/|telegram\.me/|\.\w{2,3}/", re.IGNORECASE)

# Example abusive words list (expand with Hindi + English slang)
ABUSIVE = {"badword","chut","bhosd","examplebad", # English abusive / sexual / vulgar
    "fuck","fucker","motherfucker","mf","asshole","bitch","bastard","dick","cock","pussy",
    "slut","whore","nude","suck","shit","crap","dumb","stupid","idiot","retard","jerk",
    "loser","moron","pervert","porn","boobs","tits","balls","sex","cum","horny","sperm",
    "nipple","handjob","blowjob","anal","dildo","vibrator","lust","suckmy","deepthroat",
    "banging","fingering","fuckboy","fuckgirl","fuckbuddy","screw","jerking","jerkoff",
    "nasty","perv","horn","sucker","cockhead","puss","pussie","cumshot","whoring","moan",
    "nudes","strip","threesome","orgasm","boob","boobie","ass","asslick","kissmyass",

    # Hindi transliterated / Hinglish
    "chutiya","chutiye","chut","chutmarika","bhosdi","bhosdike","madarchod","behenchod",
    "lund","randi","gaand","gand","kutte","kuttiya","tatti","haraami","haraamzade",
    "laude","launde","chinal","choot","gandu","suar","bakchod","chakka","teribaap",
    "terimaa","maa","behen","betichod","lavde","bhadwe","bhadwa","rakhail","kamina",
    "kamini","nalayak","ullu","ullu ke pathe","kutte ke","kamine","kutta","bhosdiwala",
    "moot","mootra","randi ke","rand","laundi","beizzati","madharchod","suar ke bacche",
    "behen ke laude","maa ka","behen ke","beti ke","aand","aandu","aandfaad","chodu",
    "choda","chodna","gaandmasti","gaandfat","madar","bkl","bsdk","mc","bc","mkc","chod",
    "maderchod","madarjod","harami","haramkhor","haraamzada","chinal","kaminey","rakhail",
    "kutti","kuttiya","randwa","randy","tattiya","beizzati","beiman","ullu ke bacche",
    "tatte","tatta","tattya","chutke","chutiyon","chutiyo","bhosri","bhonsdi","bhonsda",
    "behnchod","madarchod","bhenchod","maa chod","behen chod","maa behen","randichod",
    "kutte kamine","suar kamina","gandfat","gaandfaad","chodh","choda","chodne","chodna",
    "randi","randiwala","randwa","rakhail","chinal","launde","lavda","lavde","launde ke",
    "teri maa","teri behen","teri maa ki","teri behen ki","behen ke laude","maa ke lode",
    "maa ke laude","baap chod","betichod","randichod","kutte ke lode","suar ke lode",
    "gand mar","gaand mar","gand maar","chod do","chod de","chodti","chodta","chodenge",
    "chodoge","randibaaz","laundibaaz","randi ke bache","rand ke bache","randi ka beta",
    "randi ki aulad","behen ki chut","maa ki chut","maa ka bharosa","gand mein","lund mein",
    "launde ki","laude ki","laude ke","chut ke","chut ke andhar","gand ke","tatti ke",
    "chut mai","chut mein","lund ke","lund mai","randi ke bacche","randi ka loda",
    "madarchod ke bache","madarchod ka beta","madarchod ki aulad","behenchod ke bache",
    "behenchod ka beta","behenchod ki aulad","randike","bhosdike","chutiyapa","bakchodi",
    "chutmarike","bhosdiwala","chodu saala","saale","saala","sali","saliye","randwa ke",
    "lauda","launde","laundi","launde ke lode","gand ke andhar","chodkar","chudiya",
    "chud gaya","chud gya","chudegi","chud ja","chudne","chudane","chud gaya","chud ja",
    "chud rahi","chud raha","chudegi","chudega","chudne wali","chudne wala","randi log",
    "randipan","randbaazi","laundapan","rakhailpan","kuttepan","bhosdapan","chutiyapan",
    "ullu ka pattha","ullu ka bacha","ullu ke bacche","ullu ka loda","ullu ke lode",
    "bhosdi ke","madarchod ke","bhen ke lode","maa ke laude","behen ke laude","gand ke laude",

    # Mixed English-Hindi slang
    "fuckall","fattu","jhatu","jhant","jhantoo","jhantud","jhantu","jhantiyan","jhantiyapa",
    "jhantiyan","chutmarika","chodu","laundey","randipana","bhosdapanti","chutiyapanti",
    "bakchodi","bakchod","faltu","nalayak","kutta kamina","kaminey kutte","chod ke","chod gaya",
    "chud gyi","chud gyi thi","chud gayi","randibaaz","randi bazaar","randwa bazaar",
    "madarchodgiri","bhenchodgiri","laundapanti","rakhailgiri","chinalgiri","bakchodiya",
    "ullu banaya","ullu bna","ullu bnata","ullu bnayi","ullu ka bandar","ullu ka beta",
    "randipanti","bhosdapanti","chodpanti","chutiyapanti","madarchodgiri","randiya",
    "randi log","randi bazaar","randi ki aulaad","madarchod log","behenchod log",
    "randu","randua","randyu","lauda lasun","laude log","chutiyalog","madarchodlog"}  # replace with your comprehensive list

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
def extract_target_user(message):
    """
    Extract target user from reply or text command like '/warn @username' or '/warn user_id'
    """
    if message.reply_to_message:
        return message.reply_to_message.from_user

    text = (getattr(message, 'text', '') or '').strip().split()
    if len(text) > 1:
        possible = text[1]
        if possible.startswith('@'):
            return possible
        if possible.isdigit():
            return int(possible)
    return None
