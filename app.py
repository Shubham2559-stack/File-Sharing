# ================================
# APP.PY - Flask Web Server
# /watch route + token verification
# ================================

from flask import (
    Flask, request, redirect,
    render_template, abort, jsonify
)
import config
import database
import token_manager
import referral
import logging

logger = logging.getLogger(__name__)

# Flask app banao
app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# ================================
# HELPER
# ================================

def check_access(user_id):
    """
    User ko access hai?
    Premium ya valid token chahiye.
    """
    if not user_id:
        return False, "no_user"

    # Premium check
    if referral.is_premium(int(user_id)):
        return True, "premium"

    # Token check
    if token_manager.has_valid_access(int(user_id)):
        return True, "token"

    return False, "no_access"

# ================================
# ROUTES
# ================================

# --------------------------------
# Home Page
# --------------------------------
@app.route('/')
def home():
    """
    Simple home page.
    Bot ka link dikhata hai.
    """
    bot_link = f"https://t.me/{config.BOT_USERNAME}"
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Sharing Bot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: #1a1a2e;
                color: white;
            }}
            .container {{
                text-align: center;
                padding: 20px;
            }}
            h1 {{ color: #e94560; }}
            a {{
                display: inline-block;
                margin-top: 20px;
                padding: 12px 30px;
                background: #e94560;
                color: white;
                text-decoration: none;
                border-radius: 25px;
                font-size: 18px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 File Sharing Bot</h1>
            <p>Telegram bot se files access karo!</p>
            <a href="{bot_link}">
                Open Bot 🚀
            </a>
        </div>
    </body>
    </html>
    """

# --------------------------------
# /watch Route — Main Route
# --------------------------------
@app.route('/watch')
def watch():
    """
    Video player page.

    URL format:
    /watch?id=FILE_ID&user=USER_ID&token=TOKEN

    Steps:
    1. file_id check karo
    2. user_id check karo
    3. Access check karo
    4. Video player dikhao
    """

    # URL se parameters nikalo
    file_id  = request.args.get('id', '')
    user_id  = request.args.get('user', '')
    token    = request.args.get('token', '')

    # --------------------------------
    # File ID check
    # --------------------------------
    if not file_id:
        return _error_page(
            "❌ File ID missing!",
            "Invalid link. Bot se sahi link lo."
        ), 400

    # --------------------------------
    # File database mein hai?
    # --------------------------------
    file_info = database.get_file(file_id)
    if not file_info:
        return _error_page(
            "❌ File Nahi Mili!",
            "Ye file exist nahi karti ya delete ho gayi."
        ), 404

    # --------------------------------
    # User ID check
    # --------------------------------
    if not user_id:
        return _error_page(
            "🔐 Login Required!",
            f"Bot se file link use karo: "
            f"https://t.me/{config.BOT_USERNAME}"
        ), 401

    # --------------------------------
    # Access check
    # --------------------------------
    has_access, reason = check_access(user_id)

    if not has_access:
        # Bot link pe redirect karo
        bot_link = (
            f"https://t.me/{config.BOT_USERNAME}"
            f"?start=file_{file_id}"
        )
        return _error_page(
            "🔐 Access Required!",
            "Pehle bot se verify karo!",
            button_text="Verify Karo 🔐",
            button_link=bot_link
        ), 403

    # --------------------------------
    # Video type check
    # Sirf video stream kar sakte hain
    # --------------------------------
    file_type = file_info.get('file_type', '')

    if file_type != 'video':
        return _error_page(
            "❌ Video Nahi Hai!",
            f"Ye file ek {file_type} hai. "
            "Sirf videos stream ho sakti hain."
        ), 400

    # --------------------------------
    # Worker URL check
    # --------------------------------
    if not config.WORKER_URL:
        return _error_page(
            "⚙️ Worker Setup Pending",
            "Cloudflare Worker abhi setup nahi hua. "
            "Step 10 ke baad kaam karega!"
        ), 503

    # --------------------------------
    # Stream URL banao
    # Cloudflare Worker se milegi
    # --------------------------------
    telegram_file_id = file_info['file_id']
    stream_url = (
        f"{config.WORKER_URL}/stream"
        f"?file_id={telegram_file_id}"
    )

    # --------------------------------
    # Video player page dikhao
    # --------------------------------
    return render_template(
        'watch.html',
        file_name=file_info.get('file_name', 'Video'),
        stream_url=stream_url,
        file_id=file_id,
        user_id=user_id,
        access_type=reason,
        bot_username=config.BOT_USERNAME
    )

# --------------------------------
# /api/check — Access Check API
# Bot is route ko call karega
# --------------------------------
@app.route('/api/check')
def api_check():
    """
    Bot ya koi bhi access check kar sakta hai.
    Returns: JSON
    """
    user_id = request.args.get('user_id', '')

    if not user_id:
        return jsonify({
            'access': False,
            'reason': 'no_user_id'
        })

    has_access, reason = check_access(user_id)
    remaining = token_manager.get_remaining_time(
        int(user_id)
    ) if has_access else "None"

    return jsonify({
        'access':    has_access,
        'reason':    reason,
        'remaining': remaining,
        'premium':   referral.is_premium(int(user_id))
    })

# --------------------------------
# /api/file — File Info API
# --------------------------------
@app.route('/api/file/<file_id>')
def api_file(file_id):
    """
    File ki info return karta hai.
    """
    file_info = database.get_file(file_id)

    if not file_info:
        return jsonify({'error': 'File not found'}), 404

    # Sensitive info remove karo
    safe_info = {
        'unique_id': file_info['unique_id'],
        'file_name': file_info['file_name'],
        'file_type': file_info['file_type'],
        'caption':   file_info.get('caption', '')
    }
    return jsonify(safe_info)

# --------------------------------
# Health Check
# Render ke liye zaroori
# --------------------------------
@app.route('/health')
def health():
    """Server alive hai? Check karo."""
    return jsonify({
        'status':  'ok',
        'bot':     config.BOT_USERNAME,
        'files':   database.get_files_count(),
        'users':   database.get_total_users()
    })

# ================================
# ERROR PAGES
# ================================

def _error_page(title, message,
                button_text="Bot Pe Jao 🤖",
                button_link=None):
    """
    Sundar error page banata hai.
    """
    if not button_link:
        button_link = f"https://t.me/{config.BOT_USERNAME}"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <meta name="viewport"
              content="width=device-width, initial-scale=1">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                background: #1a1a2e;
                color: white;
                padding: 20px;
            }}
            .card {{
                background: #16213e;
                border-radius: 15px;
                padding: 40px 30px;
                text-align: center;
                max-width: 400px;
                width: 100%;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }}
            h1 {{
                font-size: 24px;
                margin-bottom: 15px;
                color: #e94560;
            }}
            p {{
                color: #a0a0b0;
                margin-bottom: 25px;
                line-height: 1.6;
            }}
            a {{
                display: inline-block;
                padding: 12px 30px;
                background: #e94560;
                color: white;
                text-decoration: none;
                border-radius: 25px;
                font-weight: bold;
                transition: opacity 0.2s;
            }}
            a:hover {{ opacity: 0.8; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>{title}</h1>
            <p>{message}</p>
            <a href="{button_link}">{button_text}</a>
        </div>
    </body>
    </html>
    """

# ================================
# 404 Handler
# ================================
@app.errorhandler(404)
def not_found(e):
    return _error_page(
        "404 - Page Nahi Mila!",
        "Ye page exist nahi karta."
    ), 404

# ================================
# APP RUN (Direct chalane pe)
# ================================
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
)
