GroupGuardian - final ready-to-deploy bot package

Deploy:
1. Push files to GitHub root.
2. Create Render service (Web Service or Worker) linked to this repo.
3. Set BOT_TOKEN env var in Render (your bot token).
4. (Optional) ADMIN_IDS env var: comma-separated admin IDs.
5. Build: pip install -r requirements.txt
6. Start: python main.py
7. Clear build cache on Render and redeploy.
