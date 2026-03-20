# ================================
# DATABASE.PY
# Files ka data JSON mein save karta hai
# Render pe memory reset hoti hai, isliye
# hum simple dictionary use karenge
# (Step 12 mein upgrade karenge)
# ================================

import json      # JSON padhne/likhne ke liye
import os        # File check karne ke liye
import uuid      # Unique ID banane ke liye
import logging

logger = logging.getLogger(__name__)

# --------------------------------
# File jahan data save hoga
# --------------------------------
DATA_FILE = "files_data.json"

# --------------------------------
# Data Load Karo (startup pe)
# --------------------------------
def load_data():
    """
    JSON file se data padhta hai.
    Agar file nahi hai toh khali dict return karta hai.
    """
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Data load error: {e}")
            return {}
    return {}

# --------------------------------
# Data Save Karo
# --------------------------------
def save_data(data):
    """
    Dictionary ko JSON file mein save karta hai.
    """
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Data save error: {e}")
        return False

# --------------------------------
# Memory mein data rakhna
# (bar bar file padhne se bachne ke liye)
# --------------------------------
_cache = load_data()

# --------------------------------
# Naya File Save Karo
# --------------------------------
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
    # Example: "a3f8b2c1"
    unique_id = str(uuid.uuid4()).replace('-', '')[:8]
    
    # File info store karo
    _cache[unique_id] = {
        'file_id': file_id,        # Telegram file ID
        'file_type': file_type,    # Video/document/etc
        'file_name': file_name,    # File naam
        'caption': caption,        # Description
        'unique_id': unique_id,    # Humara ID
        'upload_time': __import__('time').time()  # Upload time
    }
    
    # JSON file mein bhi save karo
    save_data(_cache)
    
    logger.info(f"File saved: {unique_id} | Type: {file_type}")
    return unique_id

# --------------------------------
# File Info Nikalo
# --------------------------------
def get_file(unique_id):
    """
    unique_id se file info nikalta hai.
    Returns: file info dict ya None
    """
    return _cache.get(unique_id, None)

# --------------------------------
# Saari Files Ki List
# --------------------------------
def get_all_files():
    """
    Saari uploaded files ki list deta hai.
    Returns: list of file dicts
    """
    return list(_cache.values())

# --------------------------------
# File Delete Karo
# --------------------------------
def delete_file(unique_id):
    """
    Database se file remove karta hai.
    """
    if unique_id in _cache:
        del _cache[unique_id]
        save_data(_cache)
        return True
    return False

# --------------------------------
# Total Files Count
# --------------------------------
def get_files_count():
    """Kitni files hain total"""
    return len(_cache)
# database.py ke END mein ye add karo
# (Baaki code same rahega)

# ================================
# USER MANAGEMENT
# Basic user tracking ke liye
# ================================

USER_FILE = "users_data.json"
_users = {}

def _load_users():
    global _users
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, 'r') as f:
                _users = json.load(f)
        except:
            _users = {}

def _save_users():
    try:
        with open(USER_FILE, 'w') as f:
            json.dump(_users, f, indent=2)
    except Exception as e:
        logger.error(f"Users save error: {e}")

_load_users()

def save_user(user_id, user_name, username=""):
    """User ko database mein save karo"""
    user_key = str(user_id)
    
    if user_key not in _users:
        # Naya user
        _users[user_key] = {
            'user_id': user_id,
            'name': user_name,
            'username': username,
            'joined_at': __import__('time').time(),
            'referred_by': None    # Step 6 mein use hoga
        }
        _save_users()
        return True  # Naya user
    
    return False  # Pehle se hai

def get_user(user_id):
    """User info nikalo"""
    return _users.get(str(user_id), None)

def get_total_users():
    """Total users count"""
    return len(_users)
