# ================================
# TOKEN_MANAGER.PY
# Token generate, verify, store karta hai
# ================================

import uuid
import time
import json
import os
import logging

logger = logging.getLogger(__name__)

# Token data file
TOKEN_FILE = "tokens_data.json"

# Memory cache
_tokens = {}

# --------------------------------
# Load tokens from file
# --------------------------------
def _load_tokens():
    """Startup pe tokens file se load karo"""
    global _tokens
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                _tokens = json.load(f)
        except:
            _tokens = {}

def _save_tokens():
    """Tokens file mein save karo"""
    try:
        with open(TOKEN_FILE, 'w') as f:
            json.dump(_tokens, f, indent=2)
    except Exception as e:
        logger.error(f"Token save error: {e}")

# Startup pe load karo
_load_tokens()

# --------------------------------
# Token Generate Karo
# --------------------------------
def generate_token(user_id):
    """
    User ke liye naya verification token banata hai.
    
    user_id = Telegram user ID
    Returns = token string (16 chars)
    """
    # Unique token banao
    token = str(uuid.uuid4()).replace('-', '')[:16].upper()
    
    # Save karo
    _tokens[str(user_id)] = {
        'token': token,
        'verified': False,        # Abhi verify nahi hua
        'created_at': time.time(),
        'verified_at': None,
        'expires_at': None        # Verify hone ke baad set hoga
    }
    
    _save_tokens()
    logger.info(f"Token generated for user {user_id}: {token}")
    return token

# --------------------------------
# Token Verify Karo
# --------------------------------
def verify_token(user_id, token, expiry_hours=24):
    """
    User ka token check karta hai.
    
    Returns: (True, "message") ya (False, "error")
    """
    user_key = str(user_id)
    
    # User ka record hai?
    if user_key not in _tokens:
        return False, "Token nahi mila! Pehle file link use karo."
    
    record = _tokens[user_key]
    
    # Token match karta hai?
    if record['token'] != token.upper():
        return False, "❌ Galat token! Sahi token use karo."
    
    # Pehle se verify hai?
    if record['verified']:
        # Expiry check karo
        if time.time() < record['expires_at']:
            remaining = int((record['expires_at'] - time.time()) / 3600)
            return True, f"✅ Pehle se verified hai! {remaining} ghante baaki hain."
        else:
            # Expire ho gaya — naya token chahiye
            record['verified'] = False
            record['expires_at'] = None
            _save_tokens()
            return False, "⏰ Token expire ho gaya! Naya link use karo."
    
    # Token 10 minute se zyada purana?
    # (Security: generate hone ke 10 min mein verify karna hoga)
    if time.time() - record['created_at'] > 600:  # 600 sec = 10 min
        return False, "⏰ Token expire ho gaya! Naya link use karo."
    
    # ✅ Verify karo!
    record['verified'] = True
    record['verified_at'] = time.time()
    record['expires_at'] = time.time() + (expiry_hours * 3600)
    
    _save_tokens()
    logger.info(f"User {user_id} verified successfully!")
    return True, "✅ Verification successful!"

# --------------------------------
# Check Karo Access Hai Ya Nahi
# --------------------------------
def has_valid_access(user_id):
    """
    User ka access valid hai?
    
    Returns: True ya False
    """
    user_key = str(user_id)
    
    if user_key not in _tokens:
        return False
    
    record = _tokens[user_key]
    
    # Verified nahi hai
    if not record['verified']:
        return False
    
    # Expires at set nahi
    if not record['expires_at']:
        return False
    
    # Time check karo
    if time.time() > record['expires_at']:
        # Expire ho gaya — reset karo
        record['verified'] = False
        _save_tokens()
        return False
    
    return True

# --------------------------------
# Access Time Remaining
# --------------------------------
def get_remaining_time(user_id):
    """
    Kitna time bacha hai access mein.
    Returns: string jaise "23 ghante 45 minute"
    """
    user_key = str(user_id)
    
    if user_key not in _tokens:
        return "No access"
    
    record = _tokens[user_key]
    
    if not record.get('expires_at'):
        return "No access"
    
    remaining_sec = record['expires_at'] - time.time()
    
    if remaining_sec <= 0:
        return "Expired"
    
    hours   = int(remaining_sec // 3600)
    minutes = int((remaining_sec % 3600) // 60)
    
    return f"{hours} ghante {minutes} minute"

# --------------------------------
# Access Grant Karo (Referral reward ke liye)
# --------------------------------
def grant_access(user_id, hours=24):
    """
    Directly access do (referral reward etc ke liye).
    """
    user_key = str(user_id)
    
    current_time = time.time()
    
    # Agar pehle se access hai toh extend karo
    if user_key in _tokens and _tokens[user_key].get('expires_at'):
        existing_expiry = _tokens[user_key]['expires_at']
        if existing_expiry > current_time:
            # Extend karo
            new_expiry = existing_expiry + (hours * 3600)
        else:
            new_expiry = current_time + (hours * 3600)
    else:
        new_expiry = current_time + (hours * 3600)
    
    _tokens[user_key] = {
        'token': _tokens.get(user_key, {}).get('token', 'GRANTED'),
        'verified': True,
        'created_at': current_time,
        'verified_at': current_time,
        'expires_at': new_expiry
    }
    
    _save_tokens()
    logger.info(f"Access granted to user {user_id} for {hours} hours")

# --------------------------------
# Cleanup Expired Tokens
# --------------------------------
def cleanup_expired():
    """
    Purane expire tokens delete karo.
    Memory bachane ke liye.
    """
    current_time = time.time()
    expired_users = []
    
    for user_id, record in _tokens.items():
        if record.get('expires_at'):
            # 7 din se zyada purana? Delete karo
            if current_time - record.get('created_at', 0) > (7 * 86400):
                expired_users.append(user_id)
    
    for user_id in expired_users:
        del _tokens[user_id]
    
    if expired_users:
        _save_tokens()
        logger.info(f"Cleaned up {len(expired_users)} expired tokens")
