# ================================
# REFERRAL.PY
# Referral system ka core logic
# ================================

import json
import os
import time
import logging

logger = logging.getLogger(__name__)

# Referral data file
REFERRAL_FILE = "referral_data.json"

# Memory cache
_referrals = {}

# --------------------------------
# Load / Save
# --------------------------------
def _load():
    global _referrals
    if os.path.exists(REFERRAL_FILE):
        try:
            with open(REFERRAL_FILE, 'r') as f:
                _referrals = json.load(f)
        except:
            _referrals = {}

def _save():
    try:
        with open(REFERRAL_FILE, 'w') as f:
            json.dump(_referrals, f, indent=2)
    except Exception as e:
        logger.error(f"Referral save error: {e}")

_load()  # Startup pe load karo

# --------------------------------
# User ka referral record banao
# --------------------------------
def _init_user(user_id):
    """
    Agar user ka record nahi hai toh banao.
    """
    key = str(user_id)
    if key not in _referrals:
        _referrals[key] = {
            'user_id':        user_id,
            'referred_by':    None,   # Kisne refer kiya
            'referral_count': 0,      # Kitne log refer kiye
            'referred_users': [],     # Refer kiye hue users list
            'pending_reward': 0,      # Claim nahi hua reward (days)
            'total_reward_claimed': 0,# Total claim kiya (days)
            'is_premium':     False,  # Premium access hai?
            'joined_at':      time.time()
        }
        _save()

# --------------------------------
# Referral Link Generate Karo
# --------------------------------
def get_referral_link(user_id, bot_username):
    """
    User ka unique referral link banata hai.
    Format: https://t.me/BOT?start=ref_USERID
    """
    return f"https://t.me/{bot_username}?start=ref_{user_id}"

# --------------------------------
# Referral Record karo
# (Jab new user aaye referral link se)
# --------------------------------
def record_referral(new_user_id, referrer_id):
    """
    New user aaya referral link se — record karo.

    new_user_id  = Jo naya aaya
    referrer_id  = Jisne refer kiya

    Returns: (True, "msg") ya (False, "reason")
    """
    new_key      = str(new_user_id)
    referrer_key = str(referrer_id)

    # Dono ka record init karo
    _init_user(new_user_id)
    _init_user(referrer_id)

    # ❌ Self-referral check
    if str(new_user_id) == str(referrer_id):
        return False, "self_referral"

    # ❌ Already referred hai?
    if _referrals[new_key]['referred_by'] is not None:
        return False, "already_referred"

    # ❌ Pehle se list mein hai?
    if new_user_id in _referrals[referrer_key]['referred_users']:
        return False, "duplicate"

    # ✅ Record karo — but reward abhi nahi
    # Reward tab milega jab new user verify kare
    _referrals[new_key]['referred_by'] = referrer_id

    _save()
    logger.info(f"Referral recorded: {new_user_id} referred by {referrer_id}")
    return True, "recorded"

# --------------------------------
# Reward Do (Verification ke baad)
# --------------------------------
def complete_referral(new_user_id):
    """
    New user ne verification complete ki —
    ab referrer ko reward do.

    Returns: referrer_id ya None
    """
    new_key = str(new_user_id)

    _init_user(new_user_id)

    referrer_id = _referrals[new_key].get('referred_by')

    if not referrer_id:
        return None  # Koi referrer nahi

    referrer_key = str(referrer_id)
    _init_user(referrer_id)

    # Already reward diya?
    if new_user_id in _referrals[referrer_key]['referred_users']:
        return None  # Duplicate reward nahi denge

    # ✅ Reward do referrer ko
    _referrals[referrer_key]['referred_users'].append(new_user_id)
    _referrals[referrer_key]['referral_count'] += 1
    _referrals[referrer_key]['pending_reward']  += 1  # 1 din reward

    # Premium check: 5 referrals = premium
    if _referrals[referrer_key]['referral_count'] >= 5:
        _referrals[referrer_key]['is_premium'] = True

    _save()
    logger.info(
        f"Referral completed: {new_user_id} → "
        f"Reward to {referrer_id}"
    )
    return referrer_id

# --------------------------------
# Referral Stats Nikalo
# --------------------------------
def get_stats(user_id):
    """
    User ki referral statistics.
    Returns: dict with all stats
    """
    _init_user(user_id)
    key = str(user_id)
    return _referrals[key].copy()

# --------------------------------
# Pending Reward Check
# --------------------------------
def get_pending_reward(user_id):
    """
    Kitne din ka reward claim karna baaki hai.
    """
    _init_user(user_id)
    return _referrals[str(user_id)]['pending_reward']

# --------------------------------
# Reward Claim Karo
# --------------------------------
def claim_reward(user_id):
    """
    User reward claim kare.
    Returns: (days_claimed, "message")
    """
    _init_user(user_id)
    key     = str(user_id)
    pending = _referrals[key]['pending_reward']

    if pending <= 0:
        return 0, "no_pending"

    # Reward clear karo
    _referrals[key]['pending_reward']        = 0
    _referrals[key]['total_reward_claimed'] += pending

    _save()
    return pending, "claimed"

# --------------------------------
# Premium Status Check
# --------------------------------
def is_premium(user_id):
    """User premium hai?"""
    _init_user(user_id)
    return _referrals[str(user_id)]['is_premium']

# --------------------------------
# Referral Count
# --------------------------------
def get_referral_count(user_id):
    """Kitne successful referrals hain"""
    _init_user(user_id)
    return _referrals[str(user_id)]['referral_count']
