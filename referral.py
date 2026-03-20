# ================================
# REFERRAL.PY - Step 7 Updated
# Referral + Reward + Premium System
# ================================

import json
import os
import time
import logging

logger = logging.getLogger(__name__)

REFERRAL_FILE = "referral_data.json"
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

_load()

# --------------------------------
# User record init
# --------------------------------
def _init_user(user_id):
    """
    Agar user ka record nahi hai toh banao.
    Har user ke liye ye fields honge.
    """
    key = str(user_id)
    if key not in _referrals:
        _referrals[key] = {
            'user_id':              user_id,
            'referred_by':          None,
            'referral_count':       0,
            'referred_users':       [],
            'pending_reward':       0,
            'total_reward_claimed': 0,
            'is_premium':           False,
            'premium_given_at':     None,
            'joined_at':            time.time()
        }
        _save()

# --------------------------------
# Referral Link
# --------------------------------
def get_referral_link(user_id, bot_username):
    """
    User ka unique referral link.
    Format: https://t.me/BOT?start=ref_USERID
    """
    return f"https://t.me/{bot_username}?start=ref_{user_id}"

# --------------------------------
# Referral Record Karo
# --------------------------------
def record_referral(new_user_id, referrer_id):
    """
    New user referral link se aaya — record karo.
    Reward abhi nahi — verify ke baad milega.

    Returns: (True, "recorded") ya (False, "reason")
    """
    new_key      = str(new_user_id)
    referrer_key = str(referrer_id)

    _init_user(new_user_id)
    _init_user(referrer_id)

    # Self-referral check
    if str(new_user_id) == str(referrer_id):
        return False, "self_referral"

    # Already referred?
    if _referrals[new_key]['referred_by'] is not None:
        return False, "already_referred"

    # Duplicate check
    if new_user_id in _referrals[referrer_key]['referred_users']:
        return False, "duplicate"

    # Record karo — reward baad mein
    _referrals[new_key]['referred_by'] = referrer_id
    _save()

    logger.info(
        f"Referral recorded: {new_user_id} "
        f"referred by {referrer_id}"
    )
    return True, "recorded"

# --------------------------------
# Referral Complete + Reward Do
# --------------------------------
def complete_referral(new_user_id):
    """
    New user ne verification ki —
    Referrer ko reward do.

    Returns: referrer_id ya None
    """
    new_key = str(new_user_id)
    _init_user(new_user_id)

    referrer_id = _referrals[new_key].get('referred_by')
    if not referrer_id:
        return None

    referrer_key = str(referrer_id)
    _init_user(referrer_id)

    # Already reward diya?
    if new_user_id in _referrals[referrer_key]['referred_users']:
        return None

    # ✅ Reward do
    _referrals[referrer_key]['referred_users'].append(new_user_id)
    _referrals[referrer_key]['referral_count'] += 1
    _referrals[referrer_key]['pending_reward']  += 1  # +1 din

    # Premium check: 5 referrals pe premium
    count = _referrals[referrer_key]['referral_count']
    if count >= 5 and not _referrals[referrer_key]['is_premium']:
        _referrals[referrer_key]['is_premium']       = True
        _referrals[referrer_key]['premium_given_at'] = time.time()
        logger.info(f"Premium granted to {referrer_id}!")

    _save()
    logger.info(
        f"Referral complete: {new_user_id} → "
        f"Reward to {referrer_id} | "
        f"Total: {count}"
    )
    return referrer_id

# --------------------------------
# Stats
# --------------------------------
def get_stats(user_id):
    """User ki referral stats"""
    _init_user(user_id)
    return _referrals[str(user_id)].copy()

# --------------------------------
# Pending Reward
# --------------------------------
def get_pending_reward(user_id):
    """Claim nahi hua reward (days)"""
    _init_user(user_id)
    return _referrals[str(user_id)]['pending_reward']

# --------------------------------
# Reward Claim
# --------------------------------
def claim_reward(user_id):
    """
    Pending reward claim karo.
    Returns: (days_claimed, status)
    """
    _init_user(user_id)
    key     = str(user_id)
    pending = _referrals[key]['pending_reward']

    if pending <= 0:
        return 0, "no_pending"

    # Claim karo
    _referrals[key]['pending_reward']        = 0
    _referrals[key]['total_reward_claimed'] += pending
    _save()

    logger.info(f"Reward claimed: {user_id} got {pending} days")
    return pending, "claimed"

# --------------------------------
# Premium Check
# --------------------------------
def is_premium(user_id):
    """
    User premium hai?
    Premium = 5+ referrals ya admin ne diya
    """
    _init_user(user_id)
    return _referrals[str(user_id)]['is_premium']

# --------------------------------
# Premium Grant (Admin ke liye)
# --------------------------------
def grant_premium(user_id):
    """Admin kisi ko bhi premium de sakta hai"""
    _init_user(user_id)
    key = str(user_id)
    _referrals[key]['is_premium']       = True
    _referrals[key]['premium_given_at'] = time.time()
    _save()
    logger.info(f"Premium manually granted to {user_id}")

# --------------------------------
# Referral Count
# --------------------------------
def get_referral_count(user_id):
    """Total successful referrals"""
    _init_user(user_id)
    return _referrals[str(user_id)]['referral_count']

# --------------------------------
# Leaderboard (Top Referrers)
# --------------------------------
def get_leaderboard(top=10):
    """
    Top referrers ki list.
    Admin /leaderboard command ke liye.
    """
    all_users = []

    for key, data in _referrals.items():
        if data['referral_count'] > 0:
            all_users.append({
                'user_id':  data['user_id'],
                'count':    data['referral_count'],
                'premium':  data['is_premium']
            })

    # Sort by count
    all_users.sort(key=lambda x: x['count'], reverse=True)
    return all_users[:top]
