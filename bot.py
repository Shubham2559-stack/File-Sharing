# ================================
# BOT.PY - Step 4 Updated
# Token verification system add kiya
# ================================

import telebot
import config
import database
import token_manager
import logging
import requests   # Shortener API ke liye

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validate
if not config.BOT_TOKEN:
    logger.error("❌ BOT_TOKEN missing!")
    exit(1)
if config.ADMIN_ID == 0:
    logger.error("❌ ADMIN_ID missing!")
    exit(1)
if not config.BOT_USERNAME:
    logger.error("❌ BOT_USERNAME missing!")
    exit(1)

logger.info(f"✅ Bot: @{config.BOT_USERNAME}")

bot = telebot.TeleBot(config.BOT_TOKEN)

# ================================
# HELPER FUNCTIONS
# ================================

def is_admin(user_id):
    return user_id == config.ADMIN_ID

def generate_share_link(unique_id):
    return f"https://t.me/{config.BOT_USERNAME}?start=file_{unique_id}"

def get_file_info_from_message(message):
    if message.video:
        f = message.video
        return f.file_id, 'video', f.file_name or 'video.mp4'
    elif message.document:
        f = message.document
        return f.file_id, 'document', f.file_name or 'document'
    elif message.photo:
        f = message.photo[-1]
        return f.file_id, 'photo', 'photo.jpg'
    elif message.audio:
        f = message.audio
        return f.file_id, 'audio', f.file_name or 'audio.mp3'
    elif message.voice:
        f = message.voice
        return f.file_id, 'voice', 'voice.ogg'
    else:
        return None, None, None

def shorten_url(long_url):
    """
    URL shortener API se link shorten karta hai.
    Agar API nahi hai toh original link return karta hai.
    """
    # API key set nahi hai?
    if not config.SHORTENER_API_KEY or not config.SHORTENER_API_URL:
        logger.warning("Shortener API not configured, using direct link")
        return long_url
    
    try:
        # API call karo
        response = requests.get(
            config.SHORTENER_API_URL,
            params={
                'api': config.SHORTENER_API_KEY,
                'url': long_url
            },
            timeout=10
        )
        data = response.json()
        
        # Shortened URL return karo
        if data.get('status') == 'success':
            return data.get('shortenedUrl', long_url)
        else:
            return long_url
            
    except Exception as e:
        logger.error(f"Shortener error: {e}")
        return long_url  # Error pe original link

def create_verification_link(user_id):
    """
    User ke liye verification flow:
    1. Token generate karo
    2. Verify URL banao
    3. Shorten karo (optional)
    Returns: shortened verification URL
    """
    # Naya token banao
    token = token_manager.generate_token(user_id)
    
    # Verify URL: user is link pe click karega
    # Phir bot mein /verify TOKEN bhejega
    verify_url = f"https://t.me/{config.BOT_USERNAME}?start=verify_{token}"
    
    # Shorten karo (ad revenue ke liye)
    short_url = shorten_url(verify_url)
    
    return short_url, token

def send_file_to_user(chat_id, file_info):
    """User ko file bhejta hai"""
    file_id   = file_info['file_id']
    file_type = file_info['file_type']
    caption   = file_info.get('caption', '') or file_info['file_name']

    try:
        if file_type == 'video':
            return bot.send_video(chat_id, file_id, caption=caption)
        elif file_type == 'document':
            return bot.send_document(chat_id, file_id, caption=caption)
        elif file_type == 'photo':
            return bot.send_photo(chat_id, file_id, caption=caption)
        elif file_type == 'audio':
            return bot.send_audio(chat_id, file_id, caption=caption)
        elif file_type == 'voice':
            return bot.send_voice(chat_id, file_id, caption=caption)
        else:
            return bot.send_document(chat_id, file_id, caption=caption)
    except Exception as e:
        logger.error(f"Send file error: {e}")
        return None

# ================================
# COMMAND HANDLERS
# ================================

@bot.message_handler(commands=['start'])
def start_command(message):
    """
    /start handler — 3 cases:
    1. Normal /start
    2. /start file_XXXX → File request
    3. /start verify_TOKEN → Token verify
    """
    user      = message.from_user
    user_name = user.first_name or "Friend"
    user_id   = user.id

    # User save karo database mein
    database.save_user(user_id, user_name, user.username or "")

    parts = message.text.split()

    # ----------------------------------------
    # Case 3: Verify token
    # /start verify_ABCD1234
    # ----------------------------------------
    if len(parts) > 1 and parts[1].startswith('verify_'):

        token = parts[1].replace('verify_', '')
        
        success, msg = token_manager.verify_token(
            user_id,
            token,
            config.TOKEN_EXPIRY_HOURS
        )

        if success:
            bot.reply_to(message, f"""
✅ **Verification Successful!**

━━━━━━━━━━━━━━━━
🎉 {user_name}, aapka access unlock ho gaya!
⏰ Valid for: {config.TOKEN_EXPIRY_HOURS} ghante
━━━━━━━━━━━━━━━━

Ab wapas file link use karo — file mil jayegi! 📁
            """, parse_mode='Markdown')
        else:
            bot.reply_to(message, f"❌ {msg}", parse_mode='Markdown')
        return

    # ----------------------------------------
    # Case 2: File request
    # /start file_XXXX
    # ----------------------------------------
    if len(parts) > 1 and parts[1].startswith('file_'):

        unique_id = parts[1].replace('file_', '')
        file_info = database.get_file(unique_id)

        if not file_info:
            bot.reply_to(message, "❌ File nahi mili! Invalid link.")
            return

        # ⭐ TOKEN CHECK KARO ⭐
        if not is_admin(user_id):  # Admin ko verify nahi karna
            if not token_manager.has_valid_access(user_id):
                
                # Verification link banao
                verify_link, token = create_verification_link(user_id)
                
                bot.reply_to(message, f"""
🔐 **Verification Required!**

━━━━━━━━━━━━━━━━
File access karne ke liye
**pehle verify karna hoga:**

👇 **Ye steps follow karo:**

**Step 1:** Neeche diye link pe click karo
**Step 2:** Page khulega — 5 second ruko
**Step 3:** Skip/Continue karo
**Step 4:** Bot mein wapas aao
**Step 5:** File automatically milegi!

🔗 **Verification Link:**
{verify_link}

━━━━━━━━━━━━━━━━
⏰ Link 10 minute mein expire hoga!
                """, parse_mode='Markdown')
                
                # File ID yaad rakhna ke liye
                # (verify ke baad denge — Step 5 mein improve karenge)
                return

        # Access hai — file bhejo
        wait_msg = bot.reply_to(message, "⏳ File bhej raha hoon...")

        sent = send_file_to_user(message.chat.id, file_info)

        if sent:
            remaining = token_manager.get_remaining_time(user_id)
            try:
                bot.delete_message(message.chat.id, wait_msg.message_id)
            except:
                pass
            
            # Access time batao
            if not is_admin(user_id):
                bot.send_message(
                    message.chat.id,
                    f"✅ File mil gayi!\n⏰ Access remaining: {remaining}",
                    parse_mode='Markdown'
                )
        else:
            bot.edit_message_text(
                "❌ Error! Baad mein try karo.",
                message.chat.id,
                wait_msg.message_id
            )
        return

    # ----------------------------------------
    # Case 1: Normal /start
    # ----------------------------------------
    if is_admin(user_id):
        text = f"""
👑 **Welcome Admin {user_name}!**

━━━━━━━━━━━━━━━━
📁 Files: {database.get_files_count()}
👥 Users: {database.get_total_users()}
━━━━━━━━━━━━━━━━

📌 **Commands:**
• /list - Files dekho
• /stats - Statistics
• /upload\\_help - Guide
        """
    else:
        text = f"""
👋 **Namaste, {user_name}!**

━━━━━━━━━━━━━━━━
🆔 Your ID: `{user_id}`
━━━━━━━━━━━━━━━━

🔗 Share link se file access karo!
        """

    bot.reply_to(message, text, parse_mode='Markdown')

# --------------------------------
# /verify Command (Manual verify)
# --------------------------------
@bot.message_handler(commands=['verify'])
def verify_command(message):
    """
    Manual token verification.
    Usage: /verify ABCD1234EFGH5678
    """
    user_id = message.from_user.id
    parts   = message.text.split()

    if len(parts) < 2:
        bot.reply_to(message, """
❓ **Token kahan hai?**

Usage: `/verify YOUR_TOKEN`

Token verification link se milta hai.
        """, parse_mode='Markdown')
        return

    token = parts[1]

    success, msg = token_manager.verify_token(
        user_id, token, config.TOKEN_EXPIRY_HOURS
    )

    if success:
        remaining = token_manager.get_remaining_time(user_id)
        bot.reply_to(message, f"""
✅ **Verified!**

⏰ Access: {remaining}

Ab file link wapas use karo! 🎉
        """, parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ {msg}", parse_mode='Markdown')

# --------------------------------
# /mystatus Command
# --------------------------------
@bot.message_handler(commands=['mystatus'])
def mystatus_command(message):
    """User apna access status check kare"""
    user_id = message.from_user.id

    if token_manager.has_valid_access(user_id):
        remaining = token_manager.get_remaining_time(user_id)
        bot.reply_to(message, f"""
✅ **Access Active Hai!**

⏰ Remaining: {remaining}
        """, parse_mode='Markdown')
    else:
        bot.reply_to(message, """
❌ **Koi Active Access Nahi!**

File link use karo verify karne ke liye.
        """, parse_mode='Markdown')

# --------------------------------
# /help
# --------------------------------
@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, """
📚 **Help Menu**

━━━━━━━━━━━━━━━━
👤 **User Commands:**
• /start - Bot shuru karo
• /verify TOKEN - Token verify karo
• /mystatus - Access status dekho
• /help - Ye menu

👑 **Admin Commands:**
• File bhejo → Auto save
• /list - All files
• /stats - Statistics
━━━━━━━━━━━━━━━━
    """, parse_mode='Markdown')

# --------------------------------
# /list (Admin)
# --------------------------------
@bot.message_handler(commands=['list'])
def list_files_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin!")
        return

    files = database.get_all_files()
    if not files:
        bot.reply_to(message, "📭 Koi file nahi!")
        return

    text = f"📁 **Files: {len(files)}**\n\n━━━━━━━━━━━━━━━━\n"
    for i, file in enumerate(files[-10:], 1):
        emoji = {'video':'🎬','document':'📄','photo':'🖼️','audio':'🎵'}.get(file['file_type'],'📁')
        link  = generate_share_link(file['unique_id'])
        text += f"{i}. {emoji} `{file['unique_id']}`\n"
        text += f"    {file['file_name'][:20]}\n"
        text += f"    [Link]({link})\n\n"

    bot.reply_to(message, text, parse_mode='Markdown')

# --------------------------------
# /stats (Admin)
# --------------------------------
@bot.message_handler(commands=['stats'])
def stats_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin!")
        return

    files = database.get_all_files()
    bot.reply_to(message, f"""
📊 **Statistics**

━━━━━━━━━━━━━━━━
📁 Total Files: {len(files)}
👥 Total Users: {database.get_total_users()}
━━━━━━━━━━━━━━━━
    """, parse_mode='Markdown')

# --------------------------------
# File Upload Handler (Admin)
# --------------------------------
@bot.message_handler(
    content_types=['video','document','photo','audio','voice']
)
def handle_file_upload(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin upload kar sakta hai!")
        return

    proc = bot.reply_to(message, "⏳ Processing...")

    try:
        file_id, file_type, file_name = get_file_info_from_message(message)
        if not file_id:
            bot.edit_message_text("❌ Unsupported!", message.chat.id, proc.message_id)
            return

        unique_id  = database.save_file(
            file_id=file_id,
            file_type=file_type,
            file_name=file_name,
            caption=message.caption or ""
        )
        share_link = generate_share_link(unique_id)

        bot.edit_message_text(f"""
✅ **File Saved!**

━━━━━━━━━━━━━━━━
🆔 ID: `{unique_id}`
📝 Name: {file_name}
🎯 Type: {file_type}

🔗 **Share Link:**
`{share_link}`
━━━━━━━━━━━━━━━━
        """, message.chat.id, proc.message_id, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Upload error: {e}")
        bot.edit_message_text(f"❌ Error: {e}", message.chat.id, proc.message_id)

# --------------------------------
# /ping
# --------------------------------
@bot.message_handler(commands=['ping'])
def ping_command(message):
    bot.reply_to(message, "🏓 Pong!")

# ================================
# BOT START
# ================================
if __name__ == "__main__":
    logger.info("🤖 Bot starting...")
    # Cleanup old tokens
    token_manager.cleanup_expired()

    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        logger.error(f"Error: {e}")
