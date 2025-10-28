# Group Protection Bot

This Telegram bot automatically protects your group by:
- Deleting link messages (for non-admins)
- Muting users who use abusive words (permanent after 3 warnings)
- Showing welcome messages
- Admin-only commands: /ban, /unban, /mute, /unmute, /warn, /resetwarns

## 🚀 Deployment on Render

1. Create a new **Web Service** on [Render.com](https://render.com/)
2. Upload all files from this ZIP
3. Set **Environment Variable**:  
   - Key: `BOT_TOKEN`  
   - Value: Your Telegram bot token
4. Set **Start Command**:  
   ```bash
   python3 main.py
   ```
5. Click **Deploy** and your bot will start running 24×7.
