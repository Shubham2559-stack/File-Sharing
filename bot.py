# ================================
# BOT.PY - Step 7 Final
# Referral + Reward + Premium System
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
# VALIDATE
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

def check_access(user_id):
    """
    User ko access hai ya nahi check karo.
    Premium users ko hamesha access hai.
    Normal users ko valid token chahiye.
    Returns: (True/False, reason)
    """
    # Admin ko hamesha access
    if is_admin(user_id):
        return True, "admin"

    # Premium user — hamesha access
    if referral.is_premium(user_id):
        return True, "premium"

    # Normal user — token check
    if token_manager.has_valid_access(user_id):
        return True, "token"

    return False, "no_access"

# ================================
# COMMAND HANDLERS
# ================================

# --------------------------------
# /start
# --------------------------------
@bot.message_handler(commands=['start'])
def start_command(message):
    """
    4 cases:
    1. Normal /start
    2. /start file_XXXX
    3. /start verify_TOKEN
    4. /start ref_USERID
    """
    user      = message.from_user
    user_name = user.first_name or "Friend"
    user_id   = user.id
    parts     = message.text.split()

    # ----------------------------------------
    # Case 4: Referral
    # ----------------------------------------
    if len(parts) > 1 and parts[1].startswith('ref_'):
        referrer_id_str = parts[1].replace('ref_', '')
        try:
            referrer_id = int(referrer_id_str)
        except:
            referrer_id = None

        is_new = database.save_user(
            user_id, user_name,
            user.username or "",
            referred_by=referrer_id
        )

        if referrer_id and is_new:
            success, reason = referral.record_referral(
                user_id, referrer_id
            )
            if success:
                bot.reply_to(message, f"""
👋 **Namaste, {user_name}!**

🎉 **Referral link se aaye ho!**

━━━━━━━━━━━━━━━━
✅ Referral record ho gaya!
🎁 Verify karne pe tumhare
   dost ko reward milega!
━━━━━━━━━━━━━━━━

Koi file link use karo! 🔗
                """, parse_mode='Markdown')

            elif reason == "self_referral":
                bot.reply_to(message, f"""
👋 **Namaste, {user_name}!**

⚠️ Apna khud ka link
use nahi kar sakte! 😄
                """, parse_mode='Markdown')
            else:
                bot.reply_to(message,
                    f"👋 **Namaste, {user_name}!**\n\n"
                    "Bot mein swagat! 🤖",
                    parse_mode='Markdown'
                )
        else:
            bot.reply_to(message,
                f"👋 **Namaste, {user_name}!**\n\n"
                "Wapas aaye ho! 🤖",
                parse_mode='Markdown'
            )
        return

    # ----------------------------------------
    # Case 3: Verify token
    # ----------------------------------------
    if len(parts) > 1 and parts[1].startswith('verify_'):
        token = parts[1].replace('verify_', '')

        success, msg = token_manager.verify_token(
            user_id, token, config.TOKEN_EXPIRY_HOURS
        )

        if success:
            # Referrer ko reward do
            referrer_id = referral.complete_referral(user_id)

            if referrer_id:
                try:
                    ref_stats = referral.get_stats(referrer_id)
                    count     = ref_stats['referral_count']

                    # Premium mile toh special message
                    if count >= 5 and ref_stats['is_premium']:
                        notif = f"""
🎊 **PREMIUM UNLOCK HO GAYA!**

━━━━━━━━━━━━━━━━
🏆 5 referrals complete!
👑 Tumhe PREMIUM access mil gaya!
📊 Total referrals: {count}
━━━━━━━━━━━━━━━━

Ab verification ki zaroorat nahi! 🎉
                        """
                    else:
                        notif = f"""
🎉 **Referral Reward Mila!**

━━━━━━━━━━━━━━━━
👤 Tumhare referral ne verify kiya!
🎁 +1 din free access!
📊 Total referrals: {count}
━━━━━━━━━━━━━━━━

/reward se claim karo! 🏆
                        """
                    bot.send_message(
                        referrer_id, notif,
                        parse_mode='Markdown'
                    )
                except:
                    pass

            remaining = token_manager.get_remaining_time(user_id)
            is_prem   = referral.is_premium(user_id)

            bot.reply_to(message, f"""
✅ **Verification Successful!**

━━━━━━━━━━━━━━━━
🎉 {user_name}, access unlock!
⏰ Valid: {remaining}
👑 Premium: {'✅ Yes' if is_prem else '❌ No'}
━━━━━━━━━━━━━━━━

Ab file link wapas use karo! 📁
            """, parse_mode='Markdown')
        else:
            bot.reply_to(message, f"❌ {msg}",
                         parse_mode='Markdown')
        return

    # ----------------------------------------
    # Case 2: File request
    # ----------------------------------------
    if len(parts) > 1 and parts[1].startswith('file_'):
        database.save_user(
            user_id, user_name, user.username or ""
        )

        unique_id = parts[1].replace('file_', '')
        file_info = database.get_file(unique_id)

        if not file_info:
            bot.reply_to(message, "❌ File nahi mili!")
            return

        # Access check
        has_access, reason = check_access(user_id)

        if not has_access:
            verify_link, _ = create_verification_link(user_id)
            bot.reply_to(message, f"""
🔐 **Verification Required!**

━━━━━━━━━━━━━━━━
👇 **Steps:**

1️⃣ Link pe click karo
2️⃣ 5 sec ruko
3️⃣ Skip karo
4️⃣ Bot mein wapas aao
5️⃣ File link dobara use karo

🔗 **Verify Link:**
{verify_link}

━━━━━━━━━━━━━━━━
⏰ 10 min mein expire!
💡 5 referrals se premium lo!
            """, parse_mode='Markdown')
            return

        # Premium badge
        if reason == "premium":
            badge = "👑 Premium Access"
        elif reason == "admin":
            badge = "🔧 Admin Access"
        else:
            badge = f"⏰ {token_manager.get_remaining_time(user_id)}"

        wait_msg = bot.reply_to(message, "⏳ File bhej raha hoon...")
        sent     = send_file_to_user(message.chat.id, file_info)

        if sent:
            try:
                bot.delete_message(
                    message.chat.id, wait_msg.message_id
                )
            except:
                pass
            if not is_admin(user_id):
                bot.send_message(
                    message.chat.id,
                    f"✅ File mil gayi! | {badge}"
                )
        else:
            bot.edit_message_text(
                "❌ Error! Baad mein try karo.",
                message.chat.id, wait_msg.message_id
            )
        return

    # ----------------------------------------
    # Case 1: Normal /start
    # ----------------------------------------
    database.save_user(
        user_id, user_name, user.username or ""
    )

    if is_admin(user_id):
        bot.reply_to(message, f"""
👑 **Welcome Admin {user_name}!**

━━━━━━━━━━━━━━━━
📁 Files: {database.get_files_count()}
👥 Users: {database.get_total_users()}
━━━━━━━━━━━━━━━━

📌 **Admin Commands:**
• /list - Files
• /stats - Statistics
• /leaderboard - Top referrers
• /grantpremium ID - Premium do
• /upload\\_help - Guide
        """, parse_mode='Markdown')
    else:
        has_access, reason = check_access(user_id)
        status = "✅ Active" if has_access else "❌ Inactive"
        prem   = "👑 Yes" if referral.is_premium(user_id) else "❌ No"

        bot.reply_to(message, f"""
👋 **Namaste, {user_name}!**

━━━━━━━━━━━━━━━━
🆔 ID: `{user_id}`
🔐 Access: {status}
👑 Premium: {prem}
━━━━━━━━━━━━━━━━

📌 **Commands:**
• /refer - Referral link
• /stats - Apni stats
• /reward - Reward claim
• /mystatus - Access status
• /help - Help
        """, parse_mode='Markdown')

# --------------------------------
# /refer
# --------------------------------
@bot.message_handler(commands=['refer'])
def refer_command(message):
    user_id  = message.from_user.id
    ref_link = referral.get_referral_link(
        user_id, config.BOT_USERNAME
    )
    stats    = referral.get_stats(user_id)
    count    = stats['referral_count']
    needed   = max(0, 5 - count)

    # Progress bar banao
    filled  = min(count, 5)
    empty   = 5 - filled
    bar     = "🟩" * filled + "⬜" * empty

    bot.reply_to(message, f"""
🔗 **Tumhara Referral Link**

━━━━━━━━━━━━━━━━
`{ref_link}`

📊 **Stats:**
• 👥 Referrals: {count}
• 🎁 Pending: {stats['pending_reward']} din
• 👑 Premium: {'✅ Yes' if stats['is_premium'] else '❌ No'}

🏆 **Premium Progress:**
{bar} {count}/5
{"✅ Premium mil gaya!" if stats['is_premium'] else f"⬅️ {needed} aur chahiye!"}
━━━━━━━━━━━━━━━━

💡 Link share karo → Dost verify kare
   → Tumhe +1 din reward mile!
    """, parse_mode='Markdown')

# --------------------------------
# /reward
# --------------------------------
@bot.message_handler(commands=['reward'])
def reward_command(message):
    """Pending reward claim karo"""
    user_id = message.from_user.id
    pending = referral.get_pending_reward(user_id)

    if pending <= 0:
        bot.reply_to(message, """
❌ **Koi Pending Reward Nahi!**

━━━━━━━━━━━━━━━━
Reward pane ke liye:
1. /refer se link lo
2. Dosto ko share karo
3. Jab wo verify karen
   tumhe reward milega!
━━━━━━━━━━━━━━━━
        """, parse_mode='Markdown')
        return

    days_claimed, status = referral.claim_reward(user_id)

    if status == "claimed":
        # Token mein add karo
        token_manager.grant_access(
            user_id, hours=days_claimed * 24
        )
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
        bot.reply_to(message, "❌ Error aaya! Dobara try karo.")

# --------------------------------
# /stats
# --------------------------------
@bot.message_handler(commands=['stats'])
def stats_command(message):
    user_id = message.from_user.id

    if is_admin(user_id):
        files = database.get_all_files()
        lb    = referral.get_leaderboard(3)
        top3  = ""
        for i, u in enumerate(lb, 1):
            medal = ["🥇","🥈","🥉"][i-1]
            top3 += f"{medal} ID `{u['user_id']}` — {u['count']} refs\n"

        bot.reply_to(message, f"""
📊 **Bot Statistics**

━━━━━━━━━━━━━━━━
📁 Files: {len(files)}
👥 Users: {database.get_total_users()}

🏆 **Top Referrers:**
{top3 or "Abhi koi nahi!"}
━━━━━━━━━━━━━━━━
        """, parse_mode='Markdown')
    else:
        stats      = referral.get_stats(user_id)
        has_access, reason = check_access(user_id)
        remaining  = token_manager.get_remaining_time(user_id)
        count      = stats['referral_count']
        filled     = min(count, 5)
        bar        = "🟩" * filled + "⬜" * (5 - filled)

        bot.reply_to(message, f"""
📊 **Tumhari Stats**

━━━━━━━━━━━━━━━━
🔐 **Access:**
• Status: {'✅ Active' if has_access else '❌ Inactive'}
• Type: {reason}
• Remaining: {remaining}

🤝 **Referrals:**
• Total: {count}
• Pending Reward: {stats['pending_reward']} din
• Claimed: {stats['total_reward_claimed']} din

🏆 **Premium:**
{bar} {count}/5
• Status: {'👑 PREMIUM!' if stats['is_premium'] else f'{max(0,5-count)} aur chahiye'}
━━━━━━━━━━━━━━━━
/refer - Link lo
/reward - Reward claim karo
        """, parse_mode='Markdown')

# --------------------------------
# /mystatus
# --------------------------------
@bot.message_handler(commands=['mystatus'])
def mystatus_command(message):
    user_id    = message.from_user.id
    has_access, reason = check_access(user_id)
    remaining  = token_manager.get_remaining_time(user_id)
    is_prem    = referral.is_premium(user_id)

    if has_access:
        bot.reply_to(message, f"""
✅ **Access Active!**

━━━━━━━━━━━━━━━━
🔐 Type: {reason}
⏰ Remaining: {remaining}
👑 Premium: {'✅ Yes' if is_prem else '❌ No'}
━━━━━━━━━━━━━━━━
        """, parse_mode='Markdown')
    else:
        bot.reply_to(message, """
❌ **Koi Access Nahi!**

File link use karo verify karne ke liye.
Ya /refer se referrals karo premium ke liye!
        """, parse_mode='Markdown')

# --------------------------------
# /verify
# --------------------------------
@bot.message_handler(commands=['verify'])
def verify_command(message):
    user_id = message.from_user.id
    parts   = message.text.split()

    if len(parts) < 2:
        bot.reply_to(message,
            "Usage: `/verify YOUR_TOKEN`",
            parse_mode='Markdown'
        )
        return

    success, msg = token_manager.verify_token(
        user_id, parts[1], config.TOKEN_EXPIRY_HOURS
    )

    if success:
        referrer_id = referral.complete_referral(user_id)
        if referrer_id:
            try:
                bot.send_message(
                    referrer_id,
                    "🎉 Referral complete! /reward se claim karo!"
                )
            except:
                pass
        remaining = token_manager.get_remaining_time(user_id)
        bot.reply_to(message,
            f"✅ Verified!\n⏰ Access: {remaining}",
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, f"❌ {msg}", parse_mode='Markdown')

# --------------------------------
# /leaderboard (Admin)
# --------------------------------
@bot.message_handler(commands=['leaderboard'])
def leaderboard_command(message):
    """Top referrers ki list"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin!")
        return

    lb   = referral.get_leaderboard(10)
    text = "🏆 **Top Referrers**\n\n━━━━━━━━━━━━━━━━\n"

    if not lb:
        text += "Abhi koi referral nahi!"
    else:
        medals = ["🥇","🥈","🥉"]
        for i, u in enumerate(lb, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            prem  = "👑" if u['premium'] else ""
            text += (
                f"{medal} {prem} ID: `{u['user_id']}`"
                f" — {u['count']} referrals\n"
            )

    text += "\n━━━━━━━━━━━━━━━━"
    bot.reply_to(message, text, parse_mode='Markdown')

# --------------------------------
# /grantpremium (Admin)
# --------------------------------
@bot.message_handler(commands=['grantpremium'])
def grant_premium_command(message):
    """Admin kisi ko premium de"""
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin!")
        return

    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message,
            "Usage: `/grantpremium USER_ID`",
            parse_mode='Markdown'
        )
        return

    try:
        target_id = int(parts[1])
    except:
        bot.reply_to(message, "❌ Valid User ID do!")
        return

    referral.grant_premium(target_id)

    # User ko notify karo
    try:
        bot.send_message(
            target_id,
            "🎊 **Congratulations!**\n\n"
            "👑 Admin ne tumhe **Premium Access** de diya!\n"
            "Ab verification ki zaroorat nahi! 🎉",
            parse_mode='Markdown'
        )
    except:
        pass

    bot.reply_to(message,
        f"✅ Premium granted to `{target_id}`!",
        parse_mode='Markdown'
    )

# --------------------------------
# /help
# --------------------------------
@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, """
📚 **Help Menu**

━━━━━━━━━━━━━━━━
👤 **User:**
• /start - Bot shuru karo
• /refer - Referral link lo
• /stats - Apni stats
• /reward - Reward claim karo
• /mystatus - Access status
• /verify TOKEN - Manual verify
• /help - Ye menu

👑 **Admin:**
• File bhejo → Auto save
• /list - All files
• /stats - Bot stats
• /leaderboard - Top referrers
• /grantpremium ID - Premium do
━━━━━━━━━━━━━━━━

🏆 **Premium Kaise Milega:**
5 referrals karo → Auto premium!
    """, parse_mode='Markdown')

# --------------------------------
# /upload_help (Admin)
# --------------------------------
@bot.message_handler(commands=['upload_help'])
def upload_help_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin!")
        return
    bot.reply_to(message, """
📤 **Upload Guide**

✅ Video, Document, Photo, Audio
💡 File bhejo → Bot save kare → Link mile!
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
    for i, f in enumerate(files[-10:], 1):
        emoji = {
            'video':'🎬','document':'📄',
            'photo':'🖼️','audio':'🎵'
        }.get(f['file_type'], '📁')
        link = generate_share_link(f['unique_id'])
        text += f"{i}. {emoji} `{f['unique_id']}`\n"
        text += f"    {f['file_name'][:20]}\n"
        text += f"    [Link]({link})\n\n"

    bot.reply_to(message, text, parse_mode='Markdown')

# --------------------------------
# File Upload (Admin)
# --------------------------------
@bot.message_handler(
    content_types=['video','document','photo','audio','voice']
)
def handle_file_upload(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Sirf admin!")
        return

    proc = bot.reply_to(message, "⏳ Processing...")

    try:
        file_id, file_type, file_name = \
            get_file_info_from_message(message)

        if not file_id:
            bot.edit_message_text(
                "❌ Unsupported!",
                message.chat.id, proc.message_id
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
        """, message.chat.id, proc.message_id,
             parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Upload error: {e}")
        bot.edit_message_text(
            f"❌ Error: {e}",
            message.chat.id, proc.message_id
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
    logger.info(f"✅ Admin: {config.ADMIN_ID}")
    logger.info(f"✅ Username: @{config.BOT_USERNAME}")
    logger.info(f"📁 Files: {database.get_files_count()}")

    token_manager.cleanup_expired()

    try:
        bot.remove_webhook()
        logger.info("✅ Webhook cleared")
    except:
        pass

    time.sleep(3)
    logger.info("🚀 Polling shuru!")

    try:
        bot.infinity_polling(
            skip_pending=True,
            timeout=20,
            long_polling_timeout=20
        )
    except Exception as e:
        logger.error(f"Bot error: {e}")
