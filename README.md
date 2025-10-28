# 🤖 MGShield v4

A Telegram group moderation bot built with Aiogram 3.x — detects abuse, warns, mutes, and auto-bans users after 3 warnings.

## 🚀 Features
- Hindi + English bad word detection
- Warn, mute, unmute, ban, unban system
- Auto-ban after 3 warnings
- Sends alert in group tagging @admin
- Welcome message for new members

## 🛠️ Setup (Render)
1. Upload this repo to GitHub.
2. Go to [Render](https://render.com/) → New → Web Service.
3. Connect GitHub & select this repo.
4. Set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python main.py`
   - **Environment variable:** `BOT_TOKEN` = your BotFather token
5. Deploy ✅

## 📂 Files
- `main.py` → Entry point
- `handlers.py` → All moderation logic
- `requirements.txt` → Dependencies
