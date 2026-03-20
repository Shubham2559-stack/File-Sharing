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
    global _cache
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                _cache = json.load(f)
        except Exception as e:
            logger.error(f"Data load error: {e}")
            _cache = {}

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Data save error: {e}")
        return False

_load_data()

def save_file(file_id, file_type, file_name, caption=""):
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
    return _cache.get(unique_id, None)

def get_all_files():
    return list(_cache.values())

def delete_file(unique_id):
    if unique_id in _cache:
        del _cache[unique_id]
        save_data(_cache)
        return True
    return False

def get_files_count():
    return len(_cache)

# ================================
# USER STORAGE
# ================================

USER_FILE = "users_data.json"
_users = {}

def _load_users():
    global _users
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, 'r') as f:
                _users = json.load(f)
        except Exception as e:
            logger.error(f"Users load error: {e}")
            _users = {}

def _save_users():
    try:
        with open(USER_FILE, 'w') as f:
            json.dump(_users, f, indent=2)
    except Exception as e:
        logger.error(f"Users save error: {e}")

_load_users()

def save_user(user_id, user_name, username="", referred_by=None):
    user_key = str(user_id)
    if user_key not in _users:
        _users[user_key] = {
            'user_id':     user_id,
            'name':        user_name,
            'username':    username,
            'joined_at':   time.time(),
            'referred_by': referred_by
        }
        _save_users()
        logger.info(f"New user: {user_name} (ID: {user_id})")
        return True
    return False

def get_user(user_id):
    return _users.get(str(user_id), None)

def get_total_users():
    return len(_users)

def get_all_users():
    return list(_users.values())
