# ================================
# BOT.PY - Step 6 Updated
# Referral system add kiya
# ================================

import telebot
import config
import database
import token_manager
import referral
import logging
import requests

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
    """Gplinks se shorten karo"""
    if not config.SHORTENER_API_KEY or not config.SHORTENER_API_URL:
        return long_url
    try:
        response = requests.get(
            config.SHORTENER_API_URL,
            params={
                'api': config.SHORTENER_API_KEY,
                'url': long_url
            },
            timeout=10
        )
        data = response.json()
        if data.get('status') == 'success':
            return data.get('shortenedUrl', long_url)
        return long_url
    except:
        return long_url

def create_verification_link(user_id):
    """Token banao aur verification link do"""
    token      = token_manager.generate_token(user_id)
    verify_url = (
        f"https://t.me/{config.BOT_USERNAME}"
        f"?start=verify_{token}"
    )
    short_url = shorten_url(verify_url)
    return short_url, token

def send_file_to_user(chat_id, file_info):
    """File bhejta hai"""
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
        logger.error(f"Send error: {e}")
        return None

# ================================
# COMMAND HANDLERS
# ================================

@bot.message_handler(commands=['start'])
def start_command(message):
    """
    /start handler — 4 cases:
    1. Normal /start
    2. /start file_XXXX  → File request
    3. /start verify_TOK → Token verify
    4. /start ref_USERID → Referral link
    """
    user      = message.from_user
    user_name = user.first_name or "Friend"
    user_id   = user.id
    parts     = message.text.split()

    # ----------------------------------------
    # Case 4: Referral link
    # /start ref_123456789
    # ----------------------------------------
    if len(parts) > 1 and parts[1].startswith('ref_'):

        referrer_id = parts[1].replace('ref_', '')

        try:
            referrer_id = int(referrer_id)
        except:
            referrer_id = None

        # Pehle user save karo
        is_new = database.save_user(
            user_id,
            user_name,
            user.username or "",
            referred_by=referrer_id
        )

        if referrer_id and is_new:
            # Referral record karo
            success, reason = referral.record_referral(
                user_id,
                referrer_id
            )

            if success:
                bot.reply_to(message, f"""
👋 **Namaste, {user_name}!**

🎉 **Referral link se aaye ho!**

━━━━━━━━━━━━━━━━
✅ Tumhara referral record ho gaya!
🎁 Jab tum verify karoge —
   tumhare dost ko reward milega!
━━━━━━━━━━━━━━━━

File access karne ke liye
koi share link use karo! 🔗
                """, parse_mode='Markdown')

            elif reason == "self_referral":
                bot.reply_to(message, f"""
👋 **Namaste, {user_name}!**

⚠️ Apna khud ka referral link
use nahi kar sakte! 😄
                """, parse_mode='Markdown')

            else:
                # Normal welcome (duplicate etc)
                bot.reply_to(message, f"""
👋 **Namaste, {user_name}!**

Bot mein aapka swagat hai! 🤖
                """, parse_mode='Markdown')
        else:
            # Pehle se registered user
            bot.reply_to(message, f"""
👋 **Namaste, {user_name}!**

Bot mein wapas aaye ho! 🤖
            """, parse_mode='Markdown')

        return

    # ----------------------------------------
    # Case 3: Token verify
    # /start verify_TOKEN
    # ----------------------------------------
    if len(parts) > 1 and parts[1].startswith('verify_'):

        token   = parts[1].replace('verify_', '')
        success, msg = token_manager.verify_token(
            user_id, token, config.TOKEN_EXPIRY_HOURS
        )

        if success:
            # ⭐ Referral complete karo — referrer ko reward do
            referrer_id = referral.complete_referral(user_id)

            if referrer_id:
                # Referrer ko notify karo
                try:
                    ref_stats = referral.get_stats(referrer_id)
                    bot.send_message(
                        referrer_id,
                        f"""
🎉 **Referral Reward Mila!**

━━━━━━━━━━━━━━━━
👤 Tumhare referral ne verify kiya!
🎁 +1 din ka free access!
📊 Total referrals: {ref_stats['referral_count']}
━━━━━━━━━━━━━━━━

/reward command se claim karo! 🏆
                        """,
                        parse_mode='Markdown'
                    )
                except:
                    pass  # Referrer ne bot block kiya hoga

            remaining = token_manager.get_remaining_time(user_id)
            bot.reply_to(message, f"""
✅ **Verification Successful!**

━━━━━━━━━━━━━━━━
🎉 {user_name}, access unlock!
⏰ Valid: {remaining}
━━━━━━━━━━━━━━━━

Ab file link wapas use karo! 📁
            """, parse_mode='Markdown')

        else:
            bot.reply_to(
                message,
                f"❌ {msg}",
                parse_mode='Markdown'
            )
        return

    # ----------------------------------------
    # Case 2: File request
    # /start file_XXXX
    # ----------------------------------------
    if len(parts) > 1 and parts[1].startswith('file_'):

        # User save karo (agar naya hai)
        database.save_user(user_id, user_name, user.username or "")

        unique_id = parts[1].replace('file_', '')
        file_info = database.get_file(unique_id)

        if not file_info:
            bot.reply_to(message, "❌ File nahi mili! Invalid link.")
            return

        # Token check (admin ko nahi)
        if not is_admin(user_id):
            if not token_manager.has_valid_access(user_id):

                verify_link, _ = create_verification_link(user_id)

                bot.reply_to(message, f"""
🔐 **Verification Required!**

━━━━━━━━━━━━━━━━
👇 **Steps:**

1️⃣ Neeche link pe click karo
2️⃣ Page pe 5 sec ruko
3️⃣ Skip karo
4️⃣ Bot mein wapas aao
5️⃣ File link dobara use karo

🔗 **Verify Link:**
{verify_link}

━━━━━━━━━━━━━━━━
⏰ Link 10 min mein expire hoga!
                """, parse_mode='Markdown')
                return

        # File bhejo
        wait_msg = bot.reply_to(message, "⏳ File bhej raha hoon...")
        sent     = send_file_to_user(message.chat.id, file_info)

        if sent:
            try:
                bot.delete_message(message.chat.id, wait_msg.message_id)
            except:
                pass

            if not is_admin(user_id):
                remaining = token_manager.get_remaining_time(user_id)
                bot.send_message(
                    message.chat.id,
                    f"✅ File mil gayi!\n⏰ Access: {remaining}"
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
    database.save_user(user_id, user_name, user.username or "")

    if is_admin(user_id):
        bot.reply_to(message, f"""
👑 **Welcome Admin {user_name}!**

━━━━━━━━━━━━━━━━
📁 Files: {database.get_files_count()}
👥 Users: {database.get_total_users()}
━━━━━━━━━━━━━━━━

📌 Commands:
• /list - Files
• /stats - Statistics
• /upload\\_help - Guide
        """, parse_mode='Markdown')

    else:
        bot.reply_to(message, f"""
👋 **Namaste, {user_name}!**

━━━━━━━━━━━━━━━━
🆔 Your ID: `{user_id}`
━━━━━━━━━━━━━━━━

📌 Commands:
• /refer - Referral link lo
• /stats - Apni stats dekho
• /mystatus - Access status
• /help - Help menu
        """, parse_mode='Markdown')

# --------------------------------
# /refer Command
# --------------------------------
@bot.message_handler(commands=['refer'])
def refer_command(message):
    """User ka referral link dikhao"""
    user_id   = message.from_user.id
    user_name = message.from_user.first_name or "Friend"

    ref_link  = referral.get_referral_link(user_id, config.BOT_USERNAME)
    stats     = referral.get_stats(user_id)

    bot.reply_to(message, f"""
🔗 **Tumhara Referral Link**

━━━━━━━━━━━━━━━━
`{ref_link}`

📊 **Tumhari Stats:**
• 👥 Total Referrals: {stats['referral_count']}
• 🎁 Pending Reward: {stats['pending_reward']} din
• 👑 Premium: {'✅ Yes' if stats['is_premium'] else '❌ No'}
━━━━━━━━━━━━━━━━

💡 **Kaise Kaam Karta Hai:**
1. Upar wala link share karo
2. Dost bot join kare
3. Dost verify kare
4. Tumhe +1 din reward mile!

🏆 5 referrals = Premium access!
    """, parse_mode='Markdown')

# --------------------------------
# /stats Command (User)
# --------------------------------
@bot.message_handler(commands=['stats'])
def stats_command(message):
    """
    User: Apni referral stats dekhe
    Admin: Bot ki overall stats dekhe
    """
    user_id = message.from_user.id

    if is_admin(user_id):
        # Admin stats
        files = database.get_all_files()
        bot.reply_to(message, f"""
📊 **Bot Statistics**

━━━━━━━━━━━━━━━━
📁 Total Files: {len(files)}
👥 Total Users: {database.get_total_users()}
━━━━━━━━━━━━━━━━
        """, parse_mode='Markdown')

    else:
        # User stats
        stats     = referral.get_stats(user_id)
        remaining = token_manager.get_remaining_time(user_id)
        has_access = token_manager.has_valid_access(user_id)

        bot.reply_to(message, f"""
📊 **Tumhari Stats**

━━━━━━━━━━━━━━━━
🔐 **Access:**
• Status: {'✅ Active' if has_access else '❌ Inactive'}
• Remaining: {remaining}

🤝 **Referrals:**
• Total: {stats['referral_count']}
• Pending Reward: {stats['pending_reward']} din
• Total Claimed: {stats['total_reward_claimed']} din
• Premium: {'✅ Yes' if stats['is_premium'] else '❌ No'}
━━━━━━━━━━━━━━━━

/refer - Referral link lo
/reward - Reward claim karo
        """, parse_mode='Markdown')

# --------------------------------
# /mystatus Command
# --------------------------------
@bot.message_handler(commands=['mystatus'])
def mystatus_command(message):
    user_id = message.from_user.id

    if token_manager.has_valid_access(user_id):
        remaining = token_manager.get_remaining_time(user_id)
        bot.reply_to(message, f"""
✅ **Access Active Hai!**

⏰ Remaining: {remaining}
👑 Premium: {'✅ Yes' if referral.is_premium(user_id) else '❌ No'}
        """, parse_mode='Markdown')
    else:
        bot.reply_to(message, """
❌ **Koi Active Access Nahi!**

File link use karo verify karne ke liye.
        """, parse_mode='Markdown')

# --------------------------------
# /verify Command
# --------------------------------
@bot.message_handler(commands=['verify'])
def verify_command(message):
    user_id = message.from_user.id
    parts   = message.text.split()

    if len(parts) < 2:
        bot.reply_to(message, "Usage: `/verify YOUR_TOKEN`",
                     parse_mode='Markdown')
        return

    token   = parts[1]
    success, msg = token_manager.verify_token(
        user_id, token, config.TOKEN_EXPIRY_HOURS
    )

    if success:
        # Referral complete karo
        referrer_id = referral.complete_referral(user_id)
        if referrer_id:
            try:
                bot.send_message(
                    referrer_id,
                    "🎉 Tumhare referral ne verify kiya! "
                    "/reward se claim karo!"
                )
            except:
                pass

        remaining = token_manager.get_remaining_time(user_id)
        bot.reply_to(message,
            f"✅ Verified! Access: {remaining}",
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, f"❌ {msg}", parse_mode='Markdown')

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
• /refer - Referral link lo
• /stats - Apni stats dekho
• /reward - Reward claim karo
• /mystatus - Access status
• /verify TOKEN - Verify karo
• /help - Ye menu

👑 **Admin Commands:**
• File bhejo → Auto save
• /list - All files
• /stats - Bot stats
━━━━━━━━━━━━━━━━
    """, parse_mode='Markdown')

# --------------------------------
# /list Command (Admin)
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
    for i, f in enumerate(files[-10:], 1):
        emoji = {
            'video':'🎬','document':'📄',
            'photo':'🖼️','audio':'🎵'
        }.get(f['file_type'], '📁')
        link  = generate_share_link(f['unique_id'])
        text += f"{i}. {emoji} `{f['unique_id']}`\n"
        text += f"    {f['file_name'][:20]}\n"
        text += f"    [Link]({link})\n\n"

    bot.reply_to(message, text, parse_mode='Markdown')

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
            bot.edit_message_text(
                "❌ Unsupported!",
                message.chat.id,
                proc.message_id
            )
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
        bot.edit_message_text(
            f"❌ Error: {e}",
            message.chat.id,
            proc.message_id
        )

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
    token_manager.cleanup_expired()

    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        logger.error(f"Error: {e}")
