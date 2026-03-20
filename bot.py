# ================================
# STEP 1: Basic Telegram Bot
# ================================

import telebot          # Telegram bot library
import config           # Humari config file
import logging          # Errors/logs dikhane ke liye

# --------------------------------
# Logging Setup
# Isse console mein messages dikhenge
# --------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --------------------------------
# Bot Object Banana
# BOT_TOKEN se bot connect hota hai Telegram se
# --------------------------------
bot = telebot.TeleBot(config.BOT_TOKEN)

# --------------------------------
# /start Command Handler
# Jab user /start type kare tab ye chalega
# --------------------------------
@bot.message_handler(commands=['start'])
def start_command(message):
    """
    /start command ke liye handler
    message = jo Telegram ne bheja (user info bhi isme hai)
    """
    
    user = message.from_user  # User ki info
    user_name = user.first_name or "Friend"  # Naam ya "Friend"
    user_id = user.id  # User ka unique ID
    
    # Check karo ki admin hai ya normal user
    if user_id == config.ADMIN_ID:
        role = "👑 Admin"
    else:
        role = "👤 User"
    
    # Welcome message
    welcome_text = f"""
👋 **Namaste, {user_name}!**

🤖 **Bot mein aapka swagat hai!**

━━━━━━━━━━━━━━━━
📋 **Aapki Info:**
• 🆔 User ID: `{user_id}`
• 👤 Role: {role}
━━━━━━━━━━━━━━━━

📌 **Available Commands:**
• /start - Bot shuru karo
• /help - Help dekho

_Jaldi aur features aayenge!_ 🚀
    """
    
    # Message bhejo
    bot.reply_to(
        message,
        welcome_text,
        parse_mode='Markdown'  # Bold/italic ke liye
    )
    
    # Log karo ki kaun aaya
    logger.info(f"User {user_name} (ID: {user_id}) ne /start kiya")

# --------------------------------
# /help Command Handler
# --------------------------------
@bot.message_handler(commands=['help'])
def help_command(message):
    """
    /help command ke liye handler
    """
    
    help_text = """
📚 **Help Menu**

━━━━━━━━━━━━━━━━
🤖 **Bot Commands:**
• /start - Bot shuru karo
• /help - Ye menu dekho

🔜 **Coming Soon:**
• File upload system
• Share links
• Video streaming
• Referral system
━━━━━━━━━━━━━━━━

❓ Koi problem? Admin se contact karo.
    """
    
    bot.reply_to(message, help_text, parse_mode='Markdown')

# --------------------------------
# Unknown Commands Handler
# Jo command bot nahi jaanta
# --------------------------------
@bot.message_handler(commands=['ping'])
def ping_command(message):
    """Bot alive check karne ke liye"""
    bot.reply_to(message, "🏓 Pong! Bot alive hai!")

# --------------------------------
# Bot Start Karo (Polling)
# Ye loop chalata rehta hai aur messages check karta hai
# --------------------------------
if __name__ == "__main__":
    logger.info("🤖 Bot start ho raha hai...")
    logger.info(f"Admin ID: {config.ADMIN_ID}")
    
    try:
        # none_stop=True = error pe bhi band nahi hoga
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        logger.error(f"Bot mein error: {e}")
