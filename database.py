# ================================
# DATABASE.PY - Complete File
# Files + Users ka data store karta hai
# ================================

import json
import os
import time
import uuid
import logging

logger = logging.getLogger(__name__)

# ================================
# FILE STORAGE
# ================================

DATA_FILE = "files_data.json"
_cache = {}

def _load_data():
    """JSON file se data padhta hai"""
    global _cache
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                _cache = json.load(f)
        except Exception as e:
            logger.error(f"Data load error: {e}")
            _cache = {}

def save_data(data):
    """Dictionary ko JSON file mein save karta hai"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Data save error: {e}")
        return False

# Startup pe load karo
_load_data()

def save_file(file_id, file_type, file_name, caption=""):
    """
    Naya file database mein save karta hai.

    file_id   = Telegram ka file ID
    file_type = 'video', 'document', 'photo', etc.
    file_name = File ka naam
    caption   = File ke saath message (optional)

    Returns: unique_id (share link ke liye)
    """
    # Unique ID banao (8 characters)
    unique_id = str(uuid.uuid4()).replace('-', '')[:8]

    _cache[unique_id] = {
        'file_id':     file_id,
        'file_type':   file_type,
        'file_name':   file_name,
        'caption':     caption,
        'unique_id':   unique_id,
        'upload_time': time.time()
    }

    save_data(_cache)
    logger.info(f"File saved: {unique_id} | Type: {file_type}")
    return unique_id

def get_file(unique_id):
    """
    unique_id se file info nikalta hai.
    Returns: file info dict ya None
    """
    return _cache.get(unique_id, None)

def get_all_files():
    """
    Saari uploaded files ki list.
    Returns: list of file dicts
    """
    return list(_cache.values())

def delete_file(unique_id):
    """Database se file remove karta hai"""
    if unique_id in _cache:
        del _cache[unique_id]
        save_data(_cache)
        return True
    return False

def get_files_count():
    """Kitni files hain total"""
    return len(_cache)

# ================================
# USER STORAGE
# ================================

USER_FILE = "users_data.json"
_users = {}

def _load_users():
    """Users file se load karo"""
    global _users
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, 'r') as f:
                _users = json.load(f)
        except Exception as e:
            logger.error(f"Users load error: {e}")
            _users = {}

def _save_users():
    """Users file mein save karo"""
    try:
        with open(USER_FILE, 'w') as f:
            json.dump(_users, f, indent=2)
    except Exception as e:
        logger.error(f"Users save error: {e}")

# Startup pe load karo
_load_users()

def save_user(user_id, user_name, username="", referred_by=None):
    """
    User ko database mein save karo.

    user_id     = Telegram user ID
    user_name   = User ka naam
    username    = Telegram username (optional)
    referred_by = Jisne refer kiya uska ID (optional)

    Returns: True (naya user) ya False (pehle se hai)
    """
    user_key = str(user_id)

    if user_key not in _users:
        # Naya user — save karo
        _users[user_key] = {
            'user_id':     user_id,
            'name':        user_name,
            'username':    username,
            'joined_at':   time.time(),
            'referred_by': referred_by   # Referral system ke liye
        }
        _save_users()
        logger.info(f"New user saved: {user_name} (ID: {user_id})")
        return True   # Naya user

    return False  # Pehle se registered hai

def get_user(user_id):
    """
    User info nikalo.
    Returns: user dict ya None
    """
    return _users.get(str(user_id), None)

def get_total_users():
    """Total registered users count"""
    return len(_users)

def get_all_users():
    """
    Saare users ki list.
    Returns: list of user dicts
    """
    return list(_users.values())
