# ================================
# APP.PY - Step 11 Final
# Flask Web Server
# Bot + Website + Worker Connected
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

# Flask app
app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# ================================
# HELPER
# ================================

def check_access(user_id):
    """
    User ko access hai?
    Admin > Premium > Token > None
    """
    if not user_id:
        return False, "no_user"

    try:
        uid = int(user_id)
    except:
        return False, "invalid_user"

    # Admin check
    if uid == config.ADMIN_ID:
        return True, "admin"

    # Premium check
    if referral.is_premium(uid):
        return True, "premium"

    # Token check
    if token_manager.has_valid_access(uid):
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
    """Simple home page"""
    bot_link = f"https://t.me/{config.BOT_USERNAME}"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FileBot — File Sharing</title>
        <meta name="viewport"
              content="width=device-width, initial-scale=1">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background: #0f0f1a;
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 20px;
            }}
            .card {{
                background: #1a1a2e;
                border-radius: 20px;
                padding: 40px 30px;
                text-align: center;
                max-width: 400px;
                width: 100%;
                box-shadow: 0 10px 40px rgba(233,69,96,0.2);
                border: 1px solid #2a2a4a;
            }}
            .logo {{
                font-size: 50px;
                margin-bottom: 15px;
            }}
            h1 {{
                color: #e94560;
                font-size: 28px;
                margin-bottom: 10px;
            }}
            p {{
                color: #888;
                margin-bottom: 30px;
                line-height: 1.6;
            }}
            .stats {{
                display: flex;
                justify-content: center;
                gap: 30px;
                margin-bottom: 30px;
            }}
            .stat {{
                text-align: center;
            }}
            .stat-num {{
                font-size: 24px;
                font-weight: bold;
                color: #e94560;
            }}
            .stat-label {{
                font-size: 12px;
                color: #666;
            }}
            a.btn {{
                display: inline-block;
                padding: 14px 35px;
                background: #e94560;
                color: white;
                text-decoration: none;
                border-radius: 25px;
                font-size: 16px;
                font-weight: bold;
                transition: opacity 0.2s;
            }}
            a.btn:hover {{ opacity: 0.85; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="logo">🎬</div>
            <h1>FileBot</h1>
            <p>
                Telegram bot se files share karo
                aur videos online dekho!
            </p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-num">
                        {database.get_files_count()}
                    </div>
                    <div class="stat-label">Files</div>
                </div>
                <div class="stat">
                    <div class="stat-num">
                        {database.get_total_users()}
                    </div>
                    <div class="stat-label">Users</div>
                </div>
            </div>
            <a href="{bot_link}" class="btn">
                Open Bot 🤖
            </a>
        </div>
    </body>
    </html>
    """

# --------------------------------
# /watch Route
# --------------------------------
@app.route('/watch')
def watch():
    """
    Video player page.
    URL: /watch?id=FILE_ID&user=USER_ID
    """
    file_id = request.args.get('id', '').strip()
    user_id = request.args.get('user', '').strip()

    # File ID check
    if not file_id:
        return _error_page(
            "❌ Invalid Link!",
            "File ID missing hai. Bot se sahi link lo."
        ), 400

    # Database mein file dhundo
    file_info = database.get_file(file_id)
    if not file_info:
        return _error_page(
            "❌ File Nahi Mili!",
            "Ye file exist nahi karti ya delete ho gayi.",
            button_text="Bot Pe Jao 🤖",
            button_link=f"https://t.me/{config.BOT_USERNAME}"
        ), 404

    # User ID check
    if not user_id:
        bot_link = (
            f"https://t.me/{config.BOT_USERNAME}"
            f"?start=file_{file_id}"
        )
        return _error_page(
            "🔐 Login Required!",
            "Bot se file link use karo access karne ke liye.",
            button_text="Bot Pe Jao 🤖",
            button_link=bot_link
        ), 401

    # Access check
    has_access, reason = check_access(user_id)

    if not has_access:
        bot_link = (
            f"https://t.me/{config.BOT_USERNAME}"
            f"?start=file_{file_id}"
        )
        return _error_page(
            "🔐 Access Required!",
            "Pehle bot se verify karo! "
            "Ya 5 referrals karke premium lo.",
            button_text="Verify Karo 🔐",
            button_link=bot_link
        ), 403

    # File type check — sirf video
    file_type = file_info.get('file_type', '')
    if file_type != 'video':
        return _error_page(
            "❌ Video Nahi Hai!",
            f"Ye ek '{file_type}' file hai. "
            "Sirf video files stream ho sakti hain.",
            button_text="Bot Pe Jao 🤖",
            button_link=f"https://t.me/{config.BOT_USERNAME}"
        ), 400

    # Worker URL check
    if not config.WORKER_URL:
        return _error_page(
            "⚙️ Streaming Unavailable",
            "Video streaming abhi setup nahi hui. "
            "Baad mein try karo!",
            button_text="Bot Pe Jao 🤖",
            button_link=f"https://t.me/{config.BOT_USERNAME}"
        ), 503

    # Stream URL banao
    telegram_file_id = file_info['file_id']
    stream_url = (
        f"{config.WORKER_URL}/stream"
        f"?file_id={telegram_file_id}"
    )

    # Access time remaining
    remaining = "Premium" if reason == "premium" else \
                "Admin"   if reason == "admin"   else \
                token_manager.get_remaining_time(int(user_id))

    logger.info(
        f"Watch: file={file_id} user={user_id} "
        f"access={reason}"
    )

    return render_template(
        'watch.html',
        file_name=file_info.get('file_name', 'Video'),
        stream_url=stream_url,
        file_id=file_id,
        user_id=user_id,
        access_type=reason,
        remaining=remaining,
        bot_username=config.BOT_USERNAME
    )

# --------------------------------
# /api/check — Access Check
# --------------------------------
@app.route('/api/check')
def api_check():
    """User ka access check karo"""
    user_id = request.args.get('user_id', '')

    if not user_id:
        return jsonify({
            'access': False,
            'reason': 'no_user_id'
        })

    has_access, reason = check_access(user_id)

    try:
        uid       = int(user_id)
        remaining = token_manager.get_remaining_time(uid)
        is_prem   = referral.is_premium(uid)
    except:
        remaining = "Error"
        is_prem   = False

    return jsonify({
        'access':    has_access,
        'reason':    reason,
        'remaining': remaining,
        'premium':   is_prem
    })

# --------------------------------
# /api/file — File Info
# --------------------------------
@app.route('/api/file/<file_id>')
def api_file(file_id):
    """File info return karo"""
    file_info = database.get_file(file_id)

    if not file_info:
        return jsonify({'error': 'File not found'}), 404

    return jsonify({
        'unique_id': file_info['unique_id'],
        'file_name': file_info['file_name'],
        'file_type': file_info['file_type'],
        'caption':   file_info.get('caption', '')
    })

# --------------------------------
# /health — Health Check
# --------------------------------
@app.route('/health')
def health():
    """Server status check"""
    return jsonify({
        'status':     'ok',
        'bot':        config.BOT_USERNAME,
        'files':      database.get_files_count(),
        'users':      database.get_total_users(),
        'worker_url': config.WORKER_URL or 'not set',
        'website':    config.WEBSITE_URL or 'not set'
    })

# ================================
# ERROR PAGE HELPER
# ================================
def _error_page(
    title,
    message,
    button_text="Bot Pe Jao 🤖",
    button_link=None
):
    """Sundar error page"""
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
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background: #0f0f1a;
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 20px;
            }}
            .card {{
                background: #1a1a2e;
                border-radius: 20px;
                padding: 40px 30px;
                text-align: center;
                max-width: 400px;
                width: 100%;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                border: 1px solid #2a2a4a;
            }}
            h1 {{
                font-size: 22px;
                color: #e94560;
                margin-bottom: 15px;
            }}
            p {{
                color: #888;
                margin-bottom: 25px;
                line-height: 1.6;
                font-size: 15px;
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
# ERROR HANDLERS
# ================================
@app.errorhandler(404)
def not_found(e):
    return _error_page(
        "404 — Page Nahi Mila!",
        "Ye page exist nahi karta."
    ), 404

@app.errorhandler(500)
def server_error(e):
    return _error_page(
        "500 — Server Error!",
        "Kuch galat ho gaya. Baad mein try karo."
    ), 500

# ================================
# DIRECT RUN
# ================================
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )
