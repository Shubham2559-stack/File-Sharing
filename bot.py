# ================================
# BOT.PY - Step 2 Updated
# Admin file upload system add kiya
# ================================

import telebot
import config
import database    # Humara naya database
import logging

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --------------------------------
# Token Validate Karo
# --------------------------------
if not config.BOT_TOKEN:
    logger.error("❌ BOT_TOKEN set nahi hai!")
    exit(1)

if config.ADMIN_ID == 0:
    logger.error("❌ ADMIN_ID set nahi hai!")
    exit(1)

logger.info(f"✅ Token found: {config.BOT_TOKEN[:10]}...")
logger.info(f"✅ Admin ID: {config.ADMIN_ID}")

# Bot object banao
bot = telebot.TeleBot(config.BOT_TOKEN)

# ================================
# HELPER FUNCTIONS
# ================================

def is_admin(user_id):
    """
    Check karta hai ki user admin hai ya nahi.
    Returns: True/False
    """
    return user_id == config.ADMIN_ID

def get_file_info_from_message(message):
    """
    Message se file_id aur file_type nikalta hai.
    Telegram alag alag type se file bhejta hai.
    Returns: (file_id, file_type, file_name) ya (None, None, None)
    """
    
    # Video file
    if message.video:
        f = message.video
        return f.file_id, 'video', f.file_name or 'video.mp4'
    
    # Document (PDF, ZIP, etc.)
    elif message.document:
        f = message.document
        return f.file_id, 'document', f.file_name or 'document'
    
    # Photo
    elif message.photo:
        # Photo ka last element best quality hota hai
        f = message.photo[-1]
        return f.file_id, 'photo', 'photo.jpg'
    
    # Audio
    elif message.audio:
        f = message.audio
        return f.file_id, 'audio', f.file_name or 'audio.mp3'
    
    # Voice message
    elif message.voice:
        f = message.voice
        return f.file_id, 'voice', 'voice.ogg'
    
    # Koi file nahi
    else:
        return None, None, None

# ================================
# COMMAND HANDLERS
# ================================

# --------------------------------
# /start Command
# --------------------------------
@bot.message_handler(commands=['start'])
def start_command(message):
    """
    /start command handler
    """
    user = message.from_user
    user_name = user.first_name or "Friend"
    user_id = user.id

    if is_admin(user_id):
        # Admin ke liye special message
        text = f"""
👑 **Welcome Back, Admin {user_name}!**

━━━━━━━━━━━━━━━━
🆔 Your ID: `{user_id}`
📁 Total Files: {database.get_files_count()}
━━━━━━━━━━━━━━━━

📌 **Admin Commands:**
• /upload\\_help - Upload guide
• /list - Saari files dekho
• /stats - Bot statistics

💡 **File Upload Karna:**
Bas koi bhi file directly bhejo!
Video, Document, Photo — sab chalega!
        """
    else:
        # Normal user ke liye
        text = f"""
👋 **Namaste, {user_name}!**

🤖 **File Sharing Bot mein aapka swagat!**

━━━━━━━━━━━━━━━━
🆔 Your ID: `{user_id}`
━━━━━━━━━━━━━━━━

📌 **Commands:**
• /help - Help dekho

_Share link ke zariye files access karo!_ 🔗
        """

    bot.reply_to(message, text, parse_mode='Markdown')
    logger.info(f"User {user_name} (ID: {user_id}) ne /start kiya")

# --------------------------------
# /help Command
# --------------------------------
@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, """
📚 **Help Menu**

━━━━━━━━━━━━━━━━
👤 **User Commands:**
• /start - Bot shuru karo
• /help - Ye menu

👑 **Admin Commands:**
• File bhejo → Auto save hoga
• /list - Files dekho
• /upload\\_help - Upload guide
━━━━━━━━━━━━━━━━
    """, parse_mode='Markdown')

# --------------------------------
# /upload_help Command (Admin Only)
# --------------------------------
@bot.message_handler(commands=['upload_help'])
def upload_help_command(message):
    """Admin ke liye upload guide"""
    
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin use kar sakta hai!")
        return
    
    bot.reply_to(message, """
📤 **File Upload Guide**

━━━━━━━━━━━━━━━━
✅ **Supported Files:**
• 🎬 Video (MP4, MKV, AVI)
• 📄 Document (PDF, ZIP, etc.)
• 🖼️ Photo
• 🎵 Audio (MP3, etc.)

💡 **Kaise Upload Karein:**
1. Bas file directly bhejo
2. Caption add kar sakte ho (optional)
3. Bot automatically save kar lega
4. Unique ID milega
5. Share link generate hoga

⚠️ **Note:**
• Sirf admin upload kar sakta hai
• File Telegram ke server pe rahegi
• Hum sirf file\\_id save karte hain
━━━━━━━━━━━━━━━━
    """, parse_mode='Markdown')

# --------------------------------
# /list Command (Admin Only)
# --------------------------------
@bot.message_handler(commands=['list'])
def list_files_command(message):
    """Saari uploaded files ki list"""
    
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin use kar sakta hai!")
        return
    
    files = database.get_all_files()
    
    if not files:
        bot.reply_to(message, "📭 Abhi koi file upload nahi hui!")
        return
    
    # List banao
    text = f"📁 **Total Files: {len(files)}**\n\n━━━━━━━━━━━━━━━━\n"
    
    for i, file in enumerate(files[-10:], 1):  # Last 10 files
        # File type emoji
        emoji = {
            'video': '🎬',
            'document': '📄',
            'photo': '🖼️',
            'audio': '🎵',
            'voice': '🎤'
        }.get(file['file_type'], '📁')
        
        text += f"{i}. {emoji} `{file['unique_id']}`\n"
        text += f"    📝 {file['file_name'][:20]}\n\n"
    
    text += "━━━━━━━━━━━━━━━━\n"
    text += "_Last 10 files shown_"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# --------------------------------
# FILE UPLOAD HANDLER
# Admin jo bhi file bheje — ye handle karega
# --------------------------------
@bot.message_handler(
    content_types=['video', 'document', 'photo', 'audio', 'voice']
)
def handle_file_upload(message):
    """
    Admin ki file ko process karta hai.
    file_id nikalta hai aur database mein save karta hai.
    """
    
    # Sirf admin upload kar sakta hai
    if not is_admin(message.from_user.id):
        bot.reply_to(
            message,
            "❌ Sirf admin files upload kar sakta hai!"
        )
        return
    
    # "Processing..." message bhejo
    processing_msg = bot.reply_to(message, "⏳ File process ho rahi hai...")
    
    try:
        # File info nikalo message se
        file_id, file_type, file_name = get_file_info_from_message(message)
        
        if not file_id:
            bot.edit_message_text(
                "❌ File type supported nahi hai!",
                message.chat.id,
                processing_msg.message_id
            )
            return
        
        # Caption nikalo (agar diya ho)
        caption = message.caption or ""
        
        # Database mein save karo
        unique_id = database.save_file(
            file_id=file_id,
            file_type=file_type,
            file_name=file_name,
            caption=caption
        )
        
        # Success message
        success_text = f"""
✅ **File Successfully Saved!**

━━━━━━━━━━━━━━━━
📁 **File Details:**
• 🆔 Unique ID: `{unique_id}`
• 📝 Name: {file_name}
• 🎯 Type: {file_type}
━━━━━━━━━━━━━━━━

🔗 **Share Link:**
_(Step 3 mein banayenge)_

💾 **File ID:**
`{file_id[:30]}...`
        """
        
        # Processing message update karo
        bot.edit_message_text(
            success_text,
            message.chat.id,
            processing_msg.message_id,
            parse_mode='Markdown'
        )
        
        logger.info(f"File saved: {unique_id} | {file_type} | {file_name}")
        
    except Exception as e:
        # Error aane pe
        logger.error(f"File upload error: {e}")
        bot.edit_message_text(
            f"❌ Error aaya: {str(e)}",
            message.chat.id,
            processing_msg.message_id
        )

# --------------------------------
# /ping Command
# --------------------------------
@bot.message_handler(commands=['ping'])
def ping_command(message):
    bot.reply_to(message, "🏓 Pong! Bot alive hai!")

# ================================
# BOT START
# ================================
if __name__ == "__main__":
    logger.info("🤖 Bot start ho raha hai...")
    logger.info(f"✅ Admin ID: {config.ADMIN_ID}")
    logger.info(f"📁 Files in DB: {database.get_files_count()}")
    
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        logger.error(f"Bot error: {e}")
