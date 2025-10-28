import os
import logging
from handlers import build_application

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    # Read env
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is required.")

    webhook_base = os.environ.get("WEBHOOK_URL")  # e.g. https://your-service.onrender.com
    port = int(os.environ.get("PORT", "8443"))

    app = build_application(token=token)

    # If WEBHOOK_URL provided, run webhook mode (required on render).
    if webhook_base:
        webhook_path = f"/{token}"
        webhook_url = f"{webhook_base.rstrip('/')}{webhook_path}"
        logging.info("Starting webhook: %s (port %s, path %s)", webhook_url, port, webhook_path)
        # run_webhook will set webhook for us
        app.run_webhook(listen="0.0.0.0", port=port, path=webhook_path, webhook_url=webhook_url)
    else:
        # fallback to polling (not recommended on hosted web services)
        logging.info("WEBHOOK_URL not set - falling back to polling (not recommended on Render).")
        app.run_polling()

if __name__ == "__main__":
    main()
