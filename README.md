GuardianX - Group Protection Bot (Aiogram v3)

Deployment:
1. Push contents to GitHub repo root.
2. On Render, create a Web Service or Worker linked to the repo.
3. Set environment variable BOT_TOKEN with your bot token.
4. (Optional) Set ADMIN_IDS to comma-separated admin IDs (e.g. 7996780813).
5. Build command: pip install -r requirements.txt
6. Start command: python main.py
7. Clear build cache on Render and deploy latest commit.

Notes:
- Edit abusive_words.txt locally to add or remove slurs (one per line).
- Warnings persist in warnings.json in the repo (file-backed).
- Spam tracking is in-memory (resets on restart).
