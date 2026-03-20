# ================================
# BOT.PY - Complete Code
# Step 6 - Referral System
# ================================

import telebot
import config
import database
import token_manager
import referral
import logging
import requests
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================================
# VALIDATE CONFIG
# ================================
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
logger.info(f"✅ Admin: {config.ADMIN_ID}")

# Bot object banao
bot = telebot.TeleBot(config.BOT_TOKEN)

# ================================
# HELPER FUNCTIONS
# ================================

def is_admin(user_id):
    """Check karo admin hai ya nahi"""
    return user_id == config.ADMIN_ID

def generate_share_link(unique_id):
    """File ka share link banao"""
    return f"https://t.me/{config.BOT_USERNAME}?start=file_{unique_id}"

def get_file_info_from_message(message):
    """Message se file info nikalo"""
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
    """Gplinks se URL shorten karo"""
    if not config.SHORTENER_API_KEY or not config.SHORTENER_API_URL:
        logger.warning("Shortener not configured - using original URL")
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
        else:
            logger.warning(f"Shortener failed: {data}")
            return long_url
    except Exception as e:
        logger.error(f"Shortener error: {e}")
        return long_url

def create_verification_link(user_id):
    """
    Token banao aur verification link do.
    Returns: (short_url, token)
    """
    token = token_manager.generate_token(user_id)
    verify_url = (
        f"https://t.me/{config.BOT_USERNAME}"
        f"?start=verify_{token}"
    )
    short_url = shorten_url(verify_url)
    return short_url, token

def send_file_to_user(chat_id, file_info):
    """
    User ko file bhejta hai.
    File type ke hisaab se alag method use karta hai.
    """
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

# --------------------------------
# /start - Main Handler
# --------------------------------
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

        referrer_id_str = parts[1].replace('ref_', '')

        try:
            referrer_id = int(referrer_id_str)
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

Bot mein aapka swagat hai! 🤖
                """, parse_mode='Markdown')

            else:
                bot.reply_to(message, f"""
👋 **Namaste, {user_name}!**

🤖 Bot mein aapka swagat hai!
                """, parse_mode='Markdown')
        else:
            bot.reply_to(message, f"""
👋 **Namaste, {user_name}!**

🤖 Bot mein wapas aaye ho!
            """, parse_mode='Markdown')

        return

    # ----------------------------------------
    # Case 3: Token verify
    # /start verify_TOKEN
    # ----------------------------------------
    if len(parts) > 1 and parts[1].startswith('verify_'):

        token = parts[1].replace('verify_', '')

        success, msg = token_manager.verify_token(
            user_id,
            token,
            config.TOKEN_EXPIRY_HOURS
        )

        if success:
            # Referral complete karo — referrer ko reward do
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
🎉 {user_name}, access unlock ho gaya!
⏰ Valid for: {remaining}
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

        # User save karo
        database.save_user(
            user_id,
            user_name,
            user.username or ""
        )

        unique_id = parts[1].replace('file_', '')
        file_info = database.get_file(unique_id)

        if not file_info:
            bot.reply_to(
                message,
                "❌ File nahi mili! Invalid link."
            )
            return

        # Token check karo (admin ko nahi)
        if not is_admin(user_id):
            if not token_manager.has_valid_access(user_id):

                verify_link, _ = create_verification_link(user_id)

                bot.reply_to(message, f"""
🔐 **Verification Required!**

━━━━━━━━━━━━━━━━
👇 **Ye steps follow karo:**

1️⃣ Neeche link pe click karo
2️⃣ Page pe 5 sec ruko
3️⃣ Skip/Continue karo
4️⃣ Bot mein wapas aao
5️⃣ File link dobara use karo

🔗 **Verify Link:**
{verify_link}

━━━━━━━━━━━━━━━━
⏰ Link 10 min mein expire hoga!
                """, parse_mode='Markdown')
                return

        # File bhejo
        wait_msg = bot.reply_to(
            message,
            "⏳ File bhej raha hoon..."
        )
        sent = send_file_to_user(message.chat.id, file_info)

        if sent:
            try:
                bot.delete_message(
                    message.chat.id,
                    wait_msg.message_id
                )
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
    database.save_user(
        user_id,
        user_name,
        user.username or ""
    )

    if is_admin(user_id):
        bot.reply_to(message, f"""
👑 **Welcome Admin {user_name}!**

━━━━━━━━━━━━━━━━
📁 Files: {database.get_files_count()}
👥 Users: {database.get_total_users()}
━━━━━━━━━━━━━━━━

📌 **Admin Commands:**
• /list - Files dekho
• /stats - Statistics
• /upload\\_help - Guide
        """, parse_mode='Markdown')

    else:
        bot.reply_to(message, f"""
👋 **Namaste, {user_name}!**

━━━━━━━━━━━━━━━━
🆔 Your ID: `{user_id}`
━━━━━━━━━━━━━━━━

📌 **Commands:**
• /refer - Referral link lo
• /stats - Apni stats dekho
• /reward - Reward claim karo
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

    ref_link = referral.get_referral_link(
        user_id,
        config.BOT_USERNAME
    )
    stats = referral.get_stats(user_id)

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
# /reward Command
# --------------------------------
@bot.message_handler(commands=['reward'])
def reward_command(message):
    """
    User reward claim kare.
    Pending reward token mein add hoga.
    """
    user_id   = message.from_user.id
    user_name = message.from_user.first_name or "Friend"

    # Pending reward check karo
    pending = referral.get_pending_reward(user_id)

    if pending <= 0:
        bot.reply_to(message, """
❌ **Koi Pending Reward Nahi!**

━━━━━━━━━━━━━━━━
Reward pane ke liye:
• /refer se link lo
• Dosto ko share karo
• Jab wo verify karen
  tumhe reward milega!
━━━━━━━━━━━━━━━━
        """, parse_mode='Markdown')
        return

    # Reward claim karo
    days_claimed, status = referral.claim_reward(user_id)

    if status == "claimed":
        # Token mein days add karo
        token_manager.grant_access(user_id, hours=days_claimed * 24)
        remaining = token_manager.get_remaining_time(user_id)

        bot.reply_to(message, f"""
🎉 **Reward Claim Ho Gaya!**

━━━━━━━━━━━━━━━━
🎁 Claimed: {days_claimed} din
⏰ Total Access: {remaining}
━━━━━━━━━━━━━━━━

/refer karke aur referrals lao! 🚀
        """, parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Claim mein error aaya!")

# --------------------------------
# /stats Command
# --------------------------------
@bot.message_handler(commands=['stats'])
def stats_command(message):
    """
    User: Apni referral stats dekhe
    Admin: Bot ki overall stats dekhe
    """
    user_id = message.from_user.id

    if is_admin(user_id):
        files = database.get_all_files()
        bot.reply_to(message, f"""
📊 **Bot Statistics**

━━━━━━━━━━━━━━━━
📁 Total Files: {len(files)}
👥 Total Users: {database.get_total_users()}
━━━━━━━━━━━━━━━━
        """, parse_mode='Markdown')

    else:
        stats      = referral.get_stats(user_id)
        remaining  = token_manager.get_remaining_time(user_id)
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

/refer - Link lo
/reward - Reward claim karo
        """, parse_mode='Markdown')

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
    """Manual token verification"""
    user_id = message.from_user.id
    parts   = message.text.split()

    if len(parts) < 2:
        bot.reply_to(
            message,
            "Usage: `/verify YOUR_TOKEN`",
            parse_mode='Markdown'
        )
        return

    token = parts[1]

    success, msg = token_manager.verify_token(
        user_id,
        token,
        config.TOKEN_EXPIRY_HOURS
    )

    if success:
        # Referral complete karo
        referrer_id = referral.complete_referral(user_id)
        if referrer_id:
            try:
                bot.send_message(
                    referrer_id,
                    "🎉 Tumhare referral ne verify kiya!\n"
                    "/reward se claim karo!"
                )
            except:
                pass

        remaining = token_manager.get_remaining_time(user_id)
        bot.reply_to(
            message,
            f"✅ Verified!\n⏰ Access: {remaining}",
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, f"❌ {msg}", parse_mode='Markdown')

# --------------------------------
# /help Command
# --------------------------------
@bot.message_handler(commands=['help'])
def help_command(message):
    """Help menu"""
    bot.reply_to(message, """
📚 **Help Menu**

━━━━━━━━━━━━━━━━
👤 **User Commands:**
• /start - Bot shuru karo
• /refer - Referral link lo
• /stats - Apni stats dekho
• /reward - Reward claim karo
• /mystatus - Access status
• /verify TOKEN - Manual verify
• /help - Ye menu

👑 **Admin Commands:**
• File bhejo → Auto save
• /list - All files
• /stats - Bot stats
• /upload\\_help - Guide
━━━━━━━━━━━━━━━━
    """, parse_mode='Markdown')

# --------------------------------
# /upload_help Command (Admin)
# --------------------------------
@bot.message_handler(commands=['upload_help'])
def upload_help_command(message):
    """Admin ke liye upload guide"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin!")
        return

    bot.reply_to(message, """
📤 **Upload Guide**

━━━━━━━━━━━━━━━━
✅ **Supported Files:**
• 🎬 Video (MP4, MKV)
• 📄 Document (PDF, ZIP)
• 🖼️ Photo
• 🎵 Audio

💡 **Steps:**
1. File directly bhejo
2. Caption optional hai
3. Bot save karke link dega
4. Link share karo users se
━━━━━━━━━━━━━━━━
    """, parse_mode='Markdown')

# --------------------------------
# /list Command (Admin)
# --------------------------------
@bot.message_handler(commands=['list'])
def list_files_command(message):
    """Saari files + unke share links"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin!")
        return

    files = database.get_all_files()

    if not files:
        bot.reply_to(message, "📭 Koi file nahi!")
        return

    text = f"📁 **Total Files: {len(files)}**\n\n━━━━━━━━━━━━━━━━\n"

    for i, f in enumerate(files[-10:], 1):
        emoji = {
            'video':    '🎬',
            'document': '📄',
            'photo':    '🖼️',
            'audio':    '🎵'
        }.get(f['file_type'], '📁')

        link = generate_share_link(f['unique_id'])

        text += f"{i}. {emoji} `{f['unique_id']}`\n"
        text += f"    📝 {f['file_name'][:20]}\n"
        text += f"    🔗 [Share Link]({link})\n\n"

    text += "━━━━━━━━━━━━━━━━\n_Last 10 files_"

    bot.reply_to(message, text, parse_mode='Markdown')

# --------------------------------
# File Upload Handler (Admin)
# --------------------------------
@bot.message_handler(
    content_types=['video', 'document', 'photo', 'audio', 'voice']
)
def handle_file_upload(message):
    """Admin ki file save karke share link deta hai"""
    if not is_admin(message.from_user.id):
        bot.reply_to(
            message,
            "❌ Sirf admin files upload kar sakta hai!"
        )
        return

    proc = bot.reply_to(message, "⏳ Processing...")

    try:
        file_id, file_type, file_name = get_file_info_from_message(message)

        if not file_id:
            bot.edit_message_text(
                "❌ Unsupported file type!",
                message.chat.id,
                proc.message_id
            )
            return

        unique_id = database.save_file(
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

👆 Ye link copy karke share karo!
━━━━━━━━━━━━━━━━
        """,
            message.chat.id,
            proc.message_id,
            parse_mode='Markdown'
        )

        logger.info(f"File uploaded: {unique_id} | {file_type}")

    except Exception as e:
        logger.error(f"Upload error: {e}")
        bot.edit_message_text(
            f"❌ Error: {e}",
            message.chat.id,
            proc.message_id
        )

# --------------------------------
# /ping Command
# --------------------------------
@bot.message_handler(commands=['ping'])
def ping_command(message):
    """Bot alive check"""
    bot.reply_to(message, "🏓 Pong! Bot alive hai!")

# ================================
# BOT START
# ================================
if __name__ == "__main__":
    logger.info("🤖 Bot starting...")
    logger.info(f"✅ Admin: {config.ADMIN_ID}")
    logger.info(f"✅ Username: @{config.BOT_USERNAME}")
    logger.info(f"📁 Files: {database.get_files_count()}")

    # Cleanup old tokens
    token_manager.cleanup_expired()

    # Pehle purana webhook clear karo
    # 409 error se bachne ke liye
    try:
        bot.remove_webhook()
        logger.info("✅ Webhook cleared")
    except:
        pass

    # Thoda ruko — purana instance band ho jaye
    time.sleep(3)

    logger.info("🚀 Polling shuru ho raha hai...")

    try:
        # skip_pending = purane messages ignore karo
        bot.infinity_polling(
            skip_pending=True,
            timeout=20,
            long_polling_timeout=20
        )
    except Exception as e:
        logger.error(f"Bot error: {e}")
