# ================================
# BOT.PY - Step 3 Updated
# Share link system add kiya
# ================================

import telebot
import config
import database
import logging

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --------------------------------
# Validate Config
# --------------------------------
if not config.BOT_TOKEN:
    logger.error("❌ BOT_TOKEN set nahi hai!")
    exit(1)

if config.ADMIN_ID == 0:
    logger.error("❌ ADMIN_ID set nahi hai!")
    exit(1)

if not config.BOT_USERNAME:
    logger.error("❌ BOT_USERNAME set nahi hai!")
    exit(1)

logger.info(f"✅ Token: {config.BOT_TOKEN[:10]}...")
logger.info(f"✅ Admin ID: {config.ADMIN_ID}")
logger.info(f"✅ Bot Username: @{config.BOT_USERNAME}")

# Bot object
bot = telebot.TeleBot(config.BOT_TOKEN)

# ================================
# HELPER FUNCTIONS
# ================================

def is_admin(user_id):
    """Check karo admin hai ya nahi"""
    return user_id == config.ADMIN_ID

def generate_share_link(unique_id):
    """
    File ka share link banata hai.
    Format: https://t.me/BOT_USERNAME?start=file_UNIQUEID
    
    Example: https://t.me/myfilebot_bot?start=file_a3f8b2c1
    """
    return f"https://t.me/{config.BOT_USERNAME}?start=file_{unique_id}"

def get_file_info_from_message(message):
    """
    Message se file_id, type, name nikalta hai
    """
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

def send_file_to_user(chat_id, file_info):
    """
    User ko file bhejta hai file_type ke hisaab se.
    
    chat_id   = Kisko bhejna hai
    file_info = Database se file ki info
    """
    file_id   = file_info['file_id']
    file_type = file_info['file_type']
    caption   = file_info.get('caption', '') or file_info['file_name']

    try:
        if file_type == 'video':
            sent = bot.send_video(
                chat_id,
                file_id,
                caption=caption
            )

        elif file_type == 'document':
            sent = bot.send_document(
                chat_id,
                file_id,
                caption=caption
            )

        elif file_type == 'photo':
            sent = bot.send_photo(
                chat_id,
                file_id,
                caption=caption
            )

        elif file_type == 'audio':
            sent = bot.send_audio(
                chat_id,
                file_id,
                caption=caption
            )

        elif file_type == 'voice':
            sent = bot.send_voice(
                chat_id,
                file_id,
                caption=caption
            )

        else:
            # Unknown type — document ki tarah bhejo
            sent = bot.send_document(
                chat_id,
                file_id,
                caption=caption
            )

        return sent

    except Exception as e:
        logger.error(f"File send error: {e}")
        return None

# ================================
# COMMAND HANDLERS
# ================================

# --------------------------------
# /start Command
# File link se aane pe file bhi bhejta hai
# --------------------------------
@bot.message_handler(commands=['start'])
def start_command(message):
    """
    /start handler.
    
    2 cases:
    1. Normal /start → Welcome message
    2. /start file_a3f8b2c1 → File bhejo
    """
    user      = message.from_user
    user_name = user.first_name or "Friend"
    user_id   = user.id

    # /start ke saath kuch aaya?
    # message.text = "/start file_a3f8b2c1"
    parts = message.text.split()

    # --------------------------------
    # Case 2: File request
    # /start file_UNIQUEID
    # --------------------------------
    if len(parts) > 1 and parts[1].startswith('file_'):

        # unique_id nikalo
        # "file_a3f8b2c1" → "a3f8b2c1"
        unique_id = parts[1].replace('file_', '')

        logger.info(
            f"File request: {unique_id} by {user_name} (ID: {user_id})"
        )

        # Database mein file dhundo
        file_info = database.get_file(unique_id)

        if not file_info:
            # File nahi mili
            bot.reply_to(
                message,
                "❌ **File nahi mili!**\n\n"
                "Ye link invalid ya expired ho sakta hai.",
                parse_mode='Markdown'
            )
            return

        # "Sending..." message
        wait_msg = bot.reply_to(
            message,
            "⏳ **File bhej raha hoon...**",
            parse_mode='Markdown'
        )

        # File bhejo
        sent = send_file_to_user(message.chat.id, file_info)

        if sent:
            # Success — wait message delete karo
            try:
                bot.delete_message(message.chat.id, wait_msg.message_id)
            except:
                pass  # Delete fail ho toh koi baat nahi

            logger.info(
                f"File {unique_id} sent to {user_id}"
            )
        else:
            # Error
            bot.edit_message_text(
                "❌ File bhejne mein error aaya! Baad mein try karo.",
                message.chat.id,
                wait_msg.message_id
            )
        return

    # --------------------------------
    # Case 1: Normal /start
    # --------------------------------
    if is_admin(user_id):
        text = f"""
👑 **Welcome Back, Admin {user_name}!**

━━━━━━━━━━━━━━━━
🆔 Your ID: `{user_id}`
📁 Total Files: {database.get_files_count()}
━━━━━━━━━━━━━━━━

📌 **Admin Commands:**
• /list - Files dekho
• /upload\\_help - Upload guide
• /stats - Statistics

💡 Koi bhi file directly bhejo upload karne ke liye!
        """
    else:
        text = f"""
👋 **Namaste, {user_name}!**

🤖 **File Sharing Bot mein swagat!**

━━━━━━━━━━━━━━━━
🆔 Your ID: `{user_id}`
━━━━━━━━━━━━━━━━

🔗 Share link se file access karo!
        """

    bot.reply_to(message, text, parse_mode='Markdown')

# --------------------------------
# /help Command
# --------------------------------
@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, """
📚 **Help Menu**

━━━━━━━━━━━━━━━━
👤 **User:**
• /start - Bot shuru karo
• /help - Help menu

👑 **Admin:**
• File bhejo → Auto save + Link milega
• /list - All files
• /upload\\_help - Guide
━━━━━━━━━━━━━━━━
    """, parse_mode='Markdown')

# --------------------------------
# /list Command (Admin Only)
# --------------------------------
@bot.message_handler(commands=['list'])
def list_files_command(message):
    """Saari files + unke share links"""

    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin use kar sakta hai!")
        return

    files = database.get_all_files()

    if not files:
        bot.reply_to(message, "📭 Koi file nahi hai abhi!")
        return

    text = f"📁 **Total Files: {len(files)}**\n\n━━━━━━━━━━━━━━━━\n"

    # Last 10 files dikhao
    for i, file in enumerate(files[-10:], 1):
        emoji = {
            'video':    '🎬',
            'document': '📄',
            'photo':    '🖼️',
            'audio':    '🎵',
            'voice':    '🎤'
        }.get(file['file_type'], '📁')

        share_link = generate_share_link(file['unique_id'])

        text += f"{i}. {emoji} **{file['file_name'][:20]}**\n"
        text += f"    🆔 `{file['unique_id']}`\n"
        text += f"    🔗 [Share Link]({share_link})\n\n"

    text += "━━━━━━━━━━━━━━━━\n_Last 10 files_"

    bot.reply_to(message, text, parse_mode='Markdown')

# --------------------------------
# /upload_help Command (Admin Only)
# --------------------------------
@bot.message_handler(commands=['upload_help'])
def upload_help_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin use kar sakta hai!")
        return

    bot.reply_to(message, """
📤 **Upload Guide**

━━━━━━━━━━━━━━━━
✅ **Supported:**
• 🎬 Video (MP4, MKV)
• 📄 Document (PDF, ZIP)
• 🖼️ Photo
• 🎵 Audio

💡 **Steps:**
1. File directly bhejo bot ko
2. Caption optional hai
3. Bot save karke link dega
4. Link share karo users ke saath
━━━━━━━━━━━━━━━━
    """, parse_mode='Markdown')

# --------------------------------
# /stats Command (Admin Only)
# --------------------------------
@bot.message_handler(commands=['stats'])
def stats_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin use kar sakta hai!")
        return

    files      = database.get_all_files()
    total      = len(files)

    # Type wise count
    videos     = sum(1 for f in files if f['file_type'] == 'video')
    documents  = sum(1 for f in files if f['file_type'] == 'document')
    photos     = sum(1 for f in files if f['file_type'] == 'photo')
    others     = total - videos - documents - photos

    bot.reply_to(message, f"""
📊 **Bot Statistics**

━━━━━━━━━━━━━━━━
📁 **Files:**
• Total: {total}
• 🎬 Videos: {videos}
• 📄 Documents: {documents}
• 🖼️ Photos: {photos}
• 📦 Others: {others}

🤖 **Bot:** @{config.BOT_USERNAME}
━━━━━━━━━━━━━━━━
    """, parse_mode='Markdown')

# --------------------------------
# FILE UPLOAD HANDLER (Admin)
# --------------------------------
@bot.message_handler(
    content_types=['video', 'document', 'photo', 'audio', 'voice']
)
def handle_file_upload(message):
    """
    Admin ki file save karke share link generate karta hai
    """
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin files upload kar sakta hai!")
        return

    processing_msg = bot.reply_to(message, "⏳ Processing...")

    try:
        file_id, file_type, file_name = get_file_info_from_message(message)

        if not file_id:
            bot.edit_message_text(
                "❌ Unsupported file type!",
                message.chat.id,
                processing_msg.message_id
            )
            return

        caption   = message.caption or ""

        # Database mein save karo
        unique_id  = database.save_file(
            file_id=file_id,
            file_type=file_type,
            file_name=file_name,
            caption=caption
        )

        # Share link banao
        share_link = generate_share_link(unique_id)

        # Success message with share link
        success_text = f"""
✅ **File Saved Successfully!**

━━━━━━━━━━━━━━━━
📁 **Details:**
• 🆔 ID: `{unique_id}`
• 📝 Name: {file_name}
• 🎯 Type: {file_type}

🔗 **Share Link:**
`{share_link}`

👆 Ye link copy karke share karo!
━━━━━━━━━━━━━━━━
        """

        bot.edit_message_text(
            success_text,
            message.chat.id,
            processing_msg.message_id,
            parse_mode='Markdown'
        )

        logger.info(f"Uploaded: {unique_id} | Link: {share_link}")

    except Exception as e:
        logger.error(f"Upload error: {e}")
        bot.edit_message_text(
            f"❌ Error: {str(e)}",
            message.chat.id,
            processing_msg.message_id
        )

# --------------------------------
# /ping
# --------------------------------
@bot.message_handler(commands=['ping'])
def ping_command(message):
    bot.reply_to(message, "🏓 Pong! Bot alive hai!")

# ================================
# BOT START
# ================================
if __name__ == "__main__":
    logger.info("🤖 Bot start ho raha hai...")
    logger.info(f"✅ Admin: {config.ADMIN_ID}")
    logger.info(f"✅ Username: @{config.BOT_USERNAME}")
    logger.info(f"📁 Files: {database.get_files_count()}")

    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        logger.error(f"Bot error: {e}")
