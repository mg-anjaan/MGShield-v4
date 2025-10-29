GroupGuardian Final — Quick Start

1. Set BOT_TOKEN in Render environment variables.
2. Upload this project to Render (GitHub import or manual).
3. Ensure PORT is set (Render sets it automatically).
4. Deploy — the aiohttp /ping route keeps the app alive (Option A).
5. If you have an existing requirements.txt you want to keep, replace the included requirements.txt with your own before deploying.

Commands:
- /start
- /mute @user <time>
- /unmute @user
- /ban @user
- /unban @user
- /warn @user
- /tagall or /all (admin only)

Notes:
- Admins are completely exempt from filters (links, spam, forwarded, abusive).
- Welcome messages are simple one-line messages (first name only), auto-deleted after 10s.
- This is a minimal final package; expand word lists and refine rate-limits as needed.
