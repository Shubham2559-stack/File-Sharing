# ================================
# CONFIG.PY - Step 8 Updated
# ================================

import os

# Telegram Bot Token
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8714162717:AAHro-UFaJhw2x-Ne2EU3jCfidZ-BquKlqE")

# Admin ID
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8488620690"))

# Bot Username
BOT_USERNAME = os.environ.get("BOT_USERNAME", "zfile_robot")

# Shortener API
SHORTENER_API_KEY = os.environ.get("SHORTENER_API_KEY", "72a528cbd7a9686e99344385cda651708238c088")
SHORTENER_API_URL = os.environ.get("SHORTENER_API_URL", "https://linkshortify.com/api")

# Cloudflare Worker URL (Step 10 mein set karenge)
WORKER_URL = os.environ.get("WORKER_URL", "https://telegram-stream.infowebimpact.workers.dev/")

# Auto delete time
AUTO_DELETE_TIME = int(os.environ.get("AUTO_DELETE_TIME", "300"))

# Token expiry
TOKEN_EXPIRY_HOURS = int(os.environ.get("TOKEN_EXPIRY_HOURS", "24"))

# Flask secret key
SECRET_KEY = os.environ.get("SECRET_KEY", "mysecreetkey2026")

# Website URL (Render dega — Step 11 mein set karenge)
WEBSITE_URL = os.environ.get("WEBSITE_URL", "https://file-sharing-61f8.onrender.com")
