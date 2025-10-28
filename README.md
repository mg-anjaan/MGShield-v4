Group Protection Bot - ready to deploy (Aiogram v3)

Files:
- main.py
- handlers.py
- abusive_words.txt (list of bad words; edit locally)
- requirements.txt
- Procfile

Deployment (Render):
1. Push these files to GitHub repo root.
2. In Render, create a new service -> link repo.
3. Set Environment Variable: BOT_TOKEN = <your token>
4. Build command: pip install -r requirements.txt
5. Start command: python main.py (or use Procfile worker)
6. Clear build cache on Render and redeploy.
