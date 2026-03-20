# ================================
# CONFIG FILE - Step 3 Updated
# ================================

import os

# Telegram Bot Token
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Admin ID
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# ⭐ NAYA: Bot Username (share link ke liye zaroori!)
# @myfilebot_bot hai toh sirf "myfilebot_bot" daalo
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")

# Shortener API (Step 4 mein use hoga)
SHORTENER_API_KEY = os.environ.get("SHORTENER_API_KEY", "")
SHORTENER_API_URL = os.environ.get("SHORTENER_API_URL", "")

# Cloudflare Worker URL (Step 10 mein use hoga)
WORKER_URL = os.environ.get("WORKER_URL", "")

# Message auto-delete time (seconds)
AUTO_DELETE_TIME = int(os.environ.get("AUTO_DELETE_TIME", "300"))

# Token expiry (hours)
TOKEN_EXPIRY_HOURS = int(os.environ.get("TOKEN_EXPIRY_HOURS", "24"))
