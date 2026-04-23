import telebot
import os
import time
import sqlite3
import datetime
import json
import random
import string
import threading
from telebot import types
from flask import Flask
from threading import Thread

# --- SETTINGS ---
BOT_TOKEN = '8463540437:AAEqlG1P8RRmhJY9LVYYwugCFHF--R_BojI'  # Replace with your bot token

# Multiple Admin IDs can be added here
ADMIN_IDS = [6448344664, 6448344664]  # Add more admin IDs separated by commas
SUPER_ADMIN_IDS = [6448344664, 6448344664]  # Super admins who can manage other admins

LOG_GROUP_ID = -1003896491972  # Replace with your log group ID (must be a supergroup)

CHATS_FILE = "all_chats.txt"
DB_FILE = "files_data.db"
BACKUP_DIR = "backups"

# Create backup directory if not exists
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

bot = telebot.TeleBot(BOT_TOKEN)

# FIXED CHANNELS (Required channels users must join)
FIXED_CH = "mahfuj_offcial"
FIXED_GR = "ff_TCP_likes_bot"

# --- DATABASE FUNCTIONS ---
def init_db():
    """Initialize SQLite database and create required tables if they don't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Table for storing file information with unique keys
    cursor.execute('''CREATE TABLE IF NOT EXISTS files (
        key TEXT PRIMARY KEY, 
        file_id TEXT, 
        type TEXT, 
        caption TEXT,
        uploaded_by INTEGER,
        upload_date TIMESTAMP,
        downloads INTEGER DEFAULT 0
    )''')
    
    # Table for storing extra channel/group buttons for verification
    cursor.execute('''CREATE TABLE IF NOT EXISTS extra_menu (
        username TEXT PRIMARY KEY, 
        button_name TEXT,
        added_by INTEGER,
        added_date TIMESTAMP
    )''')
    
    # Table for storing bot statistics
    cursor.execute('''CREATE TABLE IF NOT EXISTS stats (
        stat_name TEXT PRIMARY KEY, 
        stat_value INTEGER DEFAULT 0
    )''')
    
    # Table for storing banned users
    cursor.execute('''CREATE TABLE IF NOT EXISTS banned_users (
        user_id INTEGER PRIMARY KEY, 
        reason TEXT, 
        banned_at TIMESTAMP,
        banned_by INTEGER
    )''')
    
    # Table for storing admins
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        added_by INTEGER,
        added_date TIMESTAMP,
        permissions TEXT DEFAULT 'basic'
    )''')
    
    # Table for storing user activity
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_activity (
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        last_seen TIMESTAMP,
        total_requests INTEGER DEFAULT 0,
        PRIMARY KEY (user_id)
    )''')
    
    # Table for storing file access logs
    cursor.execute('''CREATE TABLE IF NOT EXISTS file_access_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        file_key TEXT,
        access_time TIMESTAMP,
        success BOOLEAN
    )''')
    
    # Table for storing scheduled broadcasts
    cursor.execute('''CREATE TABLE IF NOT EXISTS scheduled_broadcasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT,
        scheduled_time TIMESTAMP,
        status TEXT DEFAULT 'pending',
        created_by INTEGER
    )''')
    
    # Table for storing welcome messages
    cursor.execute('''CREATE TABLE IF NOT EXISTS welcome_messages (
        chat_id INTEGER PRIMARY KEY,
        message TEXT,
        media_type TEXT,
        media_id TEXT
    )''')
    
    # Table for storing filters/auto-replies
    cursor.execute('''CREATE TABLE IF NOT EXISTS filters (
        keyword TEXT PRIMARY KEY,
        response TEXT,
        response_type TEXT,
        created_by INTEGER
    )''')
    
    # Table for storing user notes
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_notes (
        user_id INTEGER,
        note TEXT,
        created_by INTEGER,
        created_at TIMESTAMP,
        PRIMARY KEY (user_id, created_at)
    )''')
    
    # Table for storing command usage stats
    cursor.execute('''CREATE TABLE IF NOT EXISTS command_stats (
        command TEXT PRIMARY KEY,
        usage_count INTEGER DEFAULT 0
    )''')
    
    # Table for storing groups where bot is added
    cursor.execute('''CREATE TABLE IF NOT EXISTS bot_groups (
        chat_id INTEGER PRIMARY KEY,
        chat_title TEXT,
        chat_username TEXT,
        added_date TIMESTAMP,
        members_count INTEGER DEFAULT 0
    )''')
    
    # Table for storing bot settings
    cursor.execute('''CREATE TABLE IF NOT EXISTS bot_settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT
    )''')
    
    conn.commit()
    conn.close()

def log_to_group(action, user_id, details="", extra_info=None):
    """Send log to log group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get user info
        user_mention = f"<a href='tg://user?id={user_id}'>{user_id}</a>"
        
        # Create log message with HTML formatting
        log_message = f"""
<b>📋 ACTION LOG</b>

<b>Time:</b> {timestamp}
<b>Action:</b> {action}
<b>User:</b> {user_mention}

<b>Details:</b> {details}
"""
        
        if extra_info:
            log_message += f"\n<b>Extra Info:</b>\n{extra_info}"
        
        # Add formatting line
        log_message += "\n" + "─" * 30
        
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except Exception as e:
        print(f"Failed to log to group: {e}")

def log_command_usage(user_id, command):
    """Log command usage to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>⌨️ COMMAND USED</b>

<b>Time:</b> {timestamp}
<b>User:</b> <a href='tg://user?id={user_id}'>{user_id}</a>
<b>Command:</b> {command}

<b>Status:</b> ✅ Executed
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_file_upload(user_id, file_key, file_type, caption):
    """Log file upload to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>📁 FILE UPLOADED</b>

<b>Time:</b> {timestamp}
<b>Admin:</b> <a href='tg://user?id={user_id}'>{user_id}</a>
<b>File Key:</b> <code>{file_key}</code>
<b>File Type:</b> {file_type}
<b>Caption:</b> {caption[:100] if caption else 'No caption'}

<b>Link:</b> https://t.me/{bot.get_me().username}?start={file_key}
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_file_download(user_id, file_key, success):
    """Log file download to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "✅ Success" if success else "❌ Failed"
        
        log_message = f"""
<b>⬇️ FILE DOWNLOAD</b>

<b>Time:</b> {timestamp}
<b>User:</b> <a href='tg://user?id={user_id}'>{user_id}</a>
<b>File Key:</b> <code>{file_key}</code>
<b>Status:</b> {status}
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_user_joined(user_id, username, first_name):
    """Log new user to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>👤 NEW USER</b>

<b>Time:</b> {timestamp}
<b>User ID:</b> <a href='tg://user?id={user_id}'>{user_id}</a>
<b>Username:</b> @{username if username else 'N/A'}
<b>Name:</b> {first_name}
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_user_banned(user_id, reason, banned_by):
    """Log user ban to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>🚫 USER BANNED</b>

<b>Time:</b> {timestamp}
<b>Banned User:</b> <a href='tg://user?id={user_id}'>{user_id}</a>
<b>Banned By:</b> <a href='tg://user?id={banned_by}'>{banned_by}</a>
<b>Reason:</b> {reason}
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_user_unbanned(user_id, unbanned_by):
    """Log user unban to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>✅ USER UNBANNED</b>

<b>Time:</b> {timestamp}
<b>Unbanned User:</b> <a href='tg://user?id={user_id}'>{user_id}</a>
<b>Unbanned By:</b> <a href='tg://user?id={unbanned_by}'>{unbanned_by}</a>
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_admin_added(new_admin_id, added_by, permissions):
    """Log new admin addition to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>👑 NEW ADMIN</b>

<b>Time:</b> {timestamp}
<b>New Admin:</b> <a href='tg://user?id={new_admin_id}'>{new_admin_id}</a>
<b>Added By:</b> <a href='tg://user?id={added_by}'>{added_by}</a>
<b>Permissions:</b> {permissions}
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_admin_removed(admin_id, removed_by):
    """Log admin removal to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>🗑️ ADMIN REMOVED</b>

<b>Time:</b> {timestamp}
<b>Removed Admin:</b> <a href='tg://user?id={admin_id}'>{admin_id}</a>
<b>Removed By:</b> <a href='tg://user?id={removed_by}'>{removed_by}</a>
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_broadcast(admin_id, success_count, failed_count, message_preview):
    """Log broadcast to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>📢 BROADCAST SENT</b>

<b>Time:</b> {timestamp}
<b>Admin:</b> <a href='tg://user?id={admin_id}'>{admin_id}</a>
<b>Success:</b> {success_count}
<b>Failed:</b> {failed_count}

<b>Message Preview:</b>
<code>{message_preview[:200]}</code>
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_channel_added(username, button_name, added_by):
    """Log channel addition to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>🔗 CHANNEL ADDED</b>

<b>Time:</b> {timestamp}
<b>Channel:</b> @{username}
<b>Button Name:</b> {button_name}
<b>Added By:</b> <a href='tg://user?id={added_by}'>{added_by}</a>
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_channel_removed(username, removed_by):
    """Log channel removal to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>🔗 CHANNEL REMOVED</b>

<b>Time:</b> {timestamp}
<b>Channel:</b> @{username}
<b>Removed By:</b> <a href='tg://user?id={removed_by}'>{removed_by}</a>
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_group_added(chat_id, chat_title, added_by):
    """Log group addition to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>💬 BOT ADDED TO GROUP</b>

<b>Time:</b> {timestamp}
<b>Group:</b> {chat_title}
<b>Group ID:</b> <code>{chat_id}</code>
<b>Added By:</b> <a href='tg://user?id={added_by}'>{added_by}</a>
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_group_removed(chat_id, chat_title):
    """Log group removal to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>💬 BOT REMOVED FROM GROUP</b>

<b>Time:</b> {timestamp}
<b>Group:</b> {chat_title}
<b>Group ID:</b> <code>{chat_id}</code>
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_error(error_type, error_message, user_id=None):
    """Log errors to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_info = f"<a href='tg://user?id={user_id}'>{user_id}</a>" if user_id else "System"
        
        log_message = f"""
<b>⚠️ ERROR OCCURRED</b>

<b>Time:</b> {timestamp}
<b>Type:</b> {error_type}
<b>User:</b> {user_info}

<b>Error:</b>
<code>{error_message[:500]}</code>
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_system_event(event, details=""):
    """Log system events to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>⚙️ SYSTEM EVENT</b>

<b>Time:</b> {timestamp}
<b>Event:</b> {event}
<b>Details:</b> {details}
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_filter_added(keyword, response, created_by):
    """Log filter addition to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>🔍 FILTER ADDED</b>

<b>Time:</b> {timestamp}
<b>Keyword:</b> {keyword}
<b>Response:</b> {response[:100]}
<b>Added By:</b> <a href='tg://user?id={created_by}'>{created_by}</a>
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def log_filter_removed(keyword, removed_by):
    """Log filter removal to group"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_message = f"""
<b>🔍 FILTER REMOVED</b>

<b>Time:</b> {timestamp}
<b>Keyword:</b> {keyword}
<b>Removed By:</b> <a href='tg://user?id={removed_by}'>{removed_by}</a>
"""
        bot.send_message(LOG_GROUP_ID, log_message, parse_mode="HTML")
    except:
        pass

def add_admin(user_id, username, added_by, permissions='basic'):
    """Add a new admin"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO admins 
                      (user_id, username, added_by, added_date, permissions) 
                      VALUES (?, ?, ?, ?, ?)''', 
                   (user_id, username, added_by, time.time(), permissions))
    conn.commit()
    conn.close()
    if user_id not in ADMIN_IDS:
        ADMIN_IDS.append(user_id)
    
    # Log to group
    log_admin_added(user_id, added_by, permissions)

def remove_admin(user_id, removed_by):
    """Remove an admin"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM admins WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()
    if user_id in ADMIN_IDS:
        ADMIN_IDS.remove(user_id)
    
    # Log to group
    log_admin_removed(user_id, removed_by)

def get_all_admins():
    """Get list of all admins"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, permissions FROM admins')
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_extra(username, button_name, added_by):
    """Add a new channel/group to the verification list"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO extra_menu 
                      (username, button_name, added_by, added_date) 
                      VALUES (?, ?, ?, ?)''', 
                   (username, button_name, added_by, time.time()))
    conn.commit()
    conn.close()
    
    # Log to group
    log_channel_added(username, button_name, added_by)

def remove_extra(username, removed_by):
    """Remove a channel/group from the verification list"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM extra_menu WHERE username=?', (username,))
    conn.commit()
    conn.close()
    
    # Log to group
    log_channel_removed(username, removed_by)

def get_extra_list():
    """Get all extra channels/groups from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT username, button_name FROM extra_menu')
    rows = cursor.fetchall()
    conn.close()
    return rows

def save_file_to_db(key, file_id, f_type, caption, uploaded_by):
    """Save file information to database with unique key"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO files 
                      (key, file_id, type, caption, uploaded_by, upload_date) 
                      VALUES (?, ?, ?, ?, ?, ?)''', 
                   (key, file_id, f_type, caption, uploaded_by, time.time()))
    conn.commit()
    conn.close()
    
    # Log to group
    log_file_upload(uploaded_by, key, f_type, caption)

def get_file_from_db(key):
    """Retrieve file information from database using key"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT file_id, type, caption, downloads FROM files WHERE key=?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row

def increment_file_downloads(key):
    """Increment download count for a file"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE files SET downloads = downloads + 1 WHERE key=?', (key,))
    conn.commit()
    conn.close()

def delete_file_from_db(key, deleted_by):
    """Delete a file from database using its key"""
    # Get file info before deleting
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT type, caption FROM files WHERE key=?', (key,))
    file_info = cursor.fetchone()
    
    cursor.execute('DELETE FROM files WHERE key=?', (key,))
    conn.commit()
    conn.close()
    
    # Log to group
    if file_info:
        log_to_group("FILE DELETED", deleted_by, f"File Key: {key}\nType: {file_info[0]}\nCaption: {file_info[1][:50]}")

def get_all_files():
    """Get all files from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT key, type, caption, downloads, upload_date FROM files ORDER BY upload_date DESC')
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_stat(stat_name, increment=1):
    """Update bot statistics"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO stats (stat_name, stat_value) VALUES (?, 0)', (stat_name,))
    cursor.execute('UPDATE stats SET stat_value = stat_value + ? WHERE stat_name = ?', (increment, stat_name))
    conn.commit()
    conn.close()

def get_stat(stat_name):
    """Get a specific statistic value"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT stat_value FROM stats WHERE stat_name=?', (stat_name,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def ban_user(user_id, reason, banned_by):
    """Ban a user from using the bot"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO banned_users 
                      (user_id, reason, banned_at, banned_by) 
                      VALUES (?, ?, ?, ?)''', 
                   (user_id, reason, time.time(), banned_by))
    conn.commit()
    conn.close()
    
    # Log to group
    log_user_banned(user_id, reason, banned_by)

def unban_user(user_id, unbanned_by):
    """Unban a user"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM banned_users WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()
    
    # Log to group
    log_user_unbanned(user_id, unbanned_by)

def is_user_banned(user_id):
    """Check if a user is banned"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM banned_users WHERE user_id=?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def get_banned_users():
    """Get list of all banned users"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, reason, banned_at, banned_by FROM banned_users')
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_user_activity(user_id, username, first_name):
    """Update user activity"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO user_activity 
                      (user_id, username, first_name, last_seen, total_requests) 
                      VALUES (?, ?, ?, ?, COALESCE((SELECT total_requests FROM user_activity WHERE user_id=?), 0))''',
                   (user_id, username, first_name, time.time(), user_id))
    conn.commit()
    conn.close()

def log_file_access(user_id, file_key, success):
    """Log file access"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO file_access_log 
                      (user_id, file_key, access_time, success) 
                      VALUES (?, ?, ?, ?)''',
                   (user_id, file_key, time.time(), success))
    conn.commit()
    conn.close()
    if success:
        increment_file_downloads(file_key)
    
    # Log to group
    log_file_download(user_id, file_key, success)

def get_user_stats():
    """Get user statistics"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM user_activity')
    total_users = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM user_activity WHERE last_seen > ?', (time.time() - 86400,))
    active_24h = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM user_activity WHERE last_seen > ?', (time.time() - 604800,))
    active_7d = cursor.fetchone()[0]
    conn.close()
    return total_users, active_24h, active_7d

def add_filter(keyword, response, response_type, created_by):
    """Add an auto-reply filter"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO filters 
                      (keyword, response, response_type, created_by) 
                      VALUES (?, ?, ?, ?)''',
                   (keyword.lower(), response, response_type, created_by))
    conn.commit()
    conn.close()
    
    # Log to group
    log_filter_added(keyword, response, created_by)

def remove_filter(keyword, removed_by):
    """Remove a filter"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM filters WHERE keyword=?', (keyword.lower(),))
    conn.commit()
    conn.close()
    
    # Log to group
    log_filter_removed(keyword, removed_by)

def get_filter(keyword):
    """Get filter response"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT response, response_type FROM filters WHERE keyword=?', (keyword.lower(),))
    row = cursor.fetchone()
    conn.close()
    return row

def get_all_filters():
    """Get all filters"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT keyword, response, response_type FROM filters')
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_user_note(user_id, note, created_by):
    """Add a note about a user"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO user_notes 
                      (user_id, note, created_by, created_at) 
                      VALUES (?, ?, ?, ?)''',
                   (user_id, note, created_by, time.time()))
    conn.commit()
    conn.close()

def get_user_notes(user_id):
    """Get notes about a user"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT note, created_by, created_at FROM user_notes WHERE user_id=? ORDER BY created_at DESC', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def log_command(command, user_id):
    """Log command usage"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO command_stats (command, usage_count) VALUES (?, 0)', (command,))
    cursor.execute('UPDATE command_stats SET usage_count = usage_count + 1 WHERE command=?', (command,))
    conn.commit()
    conn.close()
    
    # Log command usage to group
    log_command_usage(user_id, command)

def get_command_stats():
    """Get command usage statistics"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT command, usage_count FROM command_stats ORDER BY usage_count DESC')
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_group(chat_id, chat_title, chat_username, added_by):
    """Add group to database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO bot_groups 
                      (chat_id, chat_title, chat_username, added_date) 
                      VALUES (?, ?, ?, ?)''',
                   (chat_id, chat_title, chat_username, time.time()))
    conn.commit()
    conn.close()
    
    # Log to group
    log_group_added(chat_id, chat_title, added_by)

def remove_group(chat_id, chat_title):
    """Remove group from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM bot_groups WHERE chat_id=?', (chat_id,))
    conn.commit()
    conn.close()
    
    # Log to group
    log_group_removed(chat_id, chat_title)

def get_all_groups():
    """Get all groups where bot is added"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id, chat_title, chat_username, added_date FROM bot_groups')
    rows = cursor.fetchall()
    conn.close()
    return rows

def set_setting(key, value):
    """Set bot setting"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    """Get bot setting"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key=?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def schedule_broadcast(message, scheduled_time, created_by):
    """Schedule a broadcast"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO scheduled_broadcasts 
                      (message, scheduled_time, created_by) 
                      VALUES (?, ?, ?)''',
                   (message, scheduled_time, created_by))
    conn.commit()
    conn.close()

def get_pending_broadcasts():
    """Get pending scheduled broadcasts"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''SELECT id, message, scheduled_time FROM scheduled_broadcasts 
                      WHERE status="pending" AND scheduled_time <= ?''', (time.time(),))
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_broadcast_status(broadcast_id, status):
    """Update broadcast status"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE scheduled_broadcasts SET status=? WHERE id=?', (status, broadcast_id))
    conn.commit()
    conn.close()

def backup_database():
    """Create database backup"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{BACKUP_DIR}/backup_{timestamp}.db"
    
    conn = sqlite3.connect(DB_FILE)
    backup_conn = sqlite3.connect(backup_file)
    conn.backup(backup_conn)
    backup_conn.close()
    conn.close()
    
    return backup_file

def restore_database(backup_file):
    """Restore database from backup"""
    if os.path.exists(backup_file):
        conn = sqlite3.connect(DB_FILE)
        backup_conn = sqlite3.connect(backup_file)
        backup_conn.backup(conn)
        backup_conn.close()
        conn.close()
        return True
    return False

def get_backup_files():
    """Get list of backup files"""
    if os.path.exists(BACKUP_DIR):
        return sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.db')], reverse=True)
    return []

init_db()

# Log bot start
log_system_event("BOT STARTED", f"Bot @{bot.get_me().username} is now running")

# --- USER LOGGING (FOR BROADCAST) ---
all_chats = set()
if os.path.exists(CHATS_FILE):
    with open(CHATS_FILE, "r") as f:
        for line in f:
            if line.strip():
                try: all_chats.add(int(line.strip()))
                except: continue

def log_chat(message):
    """Save user chat ID for broadcasting purposes"""
    chat_id = message.chat.id
    if chat_id > 0:  # Only log individual users, not groups
        is_new = chat_id not in all_chats
        if is_new:
            all_chats.add(chat_id)
            with open(CHATS_FILE, "a") as f:
                f.write(f"{chat_id}\n")
            update_stat('total_users')
            
            # Log new user to group
            username = message.from_user.username or ""
            first_name = message.from_user.first_name or ""
            log_user_joined(chat_id, username, first_name)
        
        # Update user activity
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""
        update_user_activity(chat_id, username, first_name)

def is_admin(user_id):
    """Check if user is an admin"""
    return user_id in ADMIN_IDS or user_id in SUPER_ADMIN_IDS

def is_super_admin(user_id):
    """Check if user is a super admin"""
    return user_id in SUPER_ADMIN_IDS

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start(message):
    """Handle /start command - Main entry point for users"""
    # Check if user is banned
    if is_user_banned(message.chat.id):
        bot.send_message(message.chat.id, "🚫 You are banned from using this bot.")
        return
    
    log_chat(message)
    chat_id = message.chat.id
    text_parts = message.text.split()
    
    # Log command usage
    log_command('/start', chat_id)

    # Handle file access via deep linking
    if len(text_parts) > 1:
        file_key = text_parts[1]
        f_data = get_file_from_db(file_key)
        
        if f_data:
            markup = types.InlineKeyboardMarkup(row_width=1)
            # Add required channels
            markup.add(types.InlineKeyboardButton("📢 Join Official Channel", url=f"https://t.me/{FIXED_CH}"))
            markup.add(types.InlineKeyboardButton("👥 Join Official Group", url=f"https://t.me/{FIXED_GR}"))
            
            # Add dynamic buttons from database
            extras = get_extra_list()
            for username, btn_name in extras:
                markup.add(types.InlineKeyboardButton(f"{btn_name}", url=f"https://t.me/{username}"))
            
            # Verification button
            markup.add(types.InlineKeyboardButton("✅ Verify & Get File", callback_data=f"check_{file_key}"))
            
            join_msg = (
                "📋 **Please join all channels to access the file:**\n\n"
                "1️⃣ First join all channels\n"
                "2️⃣ Then click **Verify & Get File**\n"
                "3️⃣ Get your file instantly\n\n"
                "⚠️ **Note:** You must join ALL channels to get access."
            )
            bot.send_message(chat_id, join_msg, reply_markup=markup, parse_mode="Markdown")
            update_stat('total_file_requests')
            return

    # Check for welcome message in groups
    welcome_msg = get_setting(f"welcome_{chat_id}")
    if welcome_msg and message.chat.type in ['group', 'supergroup']:
        new_members = message.new_chat_members
        if new_members:
            for member in new_members:
                if member.id == bot.get_me().id:
                    bot.send_message(chat_id, "👋 Thanks for adding me! Use /help to see my commands.")
                    add_group(chat_id, message.chat.title, message.chat.username, member.from_user.id if member.from_user else 0)
                else:
                    welcome_text = welcome_msg.replace("{name}", member.first_name)
                    bot.send_message(chat_id, welcome_text)

    # Admin panel for admins
    if is_admin(chat_id):
        admin_panel = (
            "╔══════════════════════╗\n"
            "║   🛡️ **ADMIN PANEL**   ║\n"
            "╚══════════════════════╝\n\n"
            
            "**📁 FILE MANAGEMENT:**\n"
            "├ `/setfile` - Upload a new file\n"
            "├ `/files` - List all files\n"
            "├ `/delfile [key]` - Delete a file\n"
            "├ `/fileinfo [key]` - File details\n"
            "├ `/topfiles` - Most downloaded files\n"
            "└ `/searchfile [query]` - Search files\n\n"
            
            "**👑 ADMIN MANAGEMENT:**\n"
            "├ `/addadmin [user_id]` - Add new admin\n"
            "├ `/removeadmin [user_id]` - Remove admin\n"
            "├ `/admins` - List all admins\n"
            "├ `/setadminperm [user_id] [perm]` - Set permissions\n"
            "└ `/adminlog [user_id]` - View admin logs\n\n"
            
            "**🔗 VERIFICATION CHANNELS:**\n"
            "├ `/add [Button Name] [@username]` - Add join button\n"
            "├ `/remove [@username]` - Remove a button\n"
            "├ `/channels` - List all channels\n"
            "├ `/setfixed [channel] [group]` - Set fixed channels\n"
            "└ `/checkmembership [user_id]` - Check user status\n\n"
            
            "**📢 BROADCAST SYSTEM:**\n"
            "├ `/broadcast [msg]` - Send to all users\n"
            "├ `/broadcastfwd [reply]` - Forward message\n"
            "├ `/schedule [time] [msg]` - Schedule broadcast\n"
            "├ `/cancelbroadcast [id]` - Cancel scheduled\n"
            "├ `/broadcaststatus` - Check broadcast status\n"
            "└ `/testbroadcast [msg]` - Test to admins\n\n"
            
            "**📊 STATISTICS:**\n"
            "├ `/stats` - Bot statistics\n"
            "├ `/userstats` - User activity stats\n"
            "├ `/filestats` - File statistics\n"
            "├ `/groupstats` - Group statistics\n"
            "├ `/commandstats` - Command usage stats\n"
            "└ `/hourlystats` - Hourly activity\n\n"
            
            "**🚫 BAN MANAGEMENT:**\n"
            "├ `/ban [user_id] [reason]` - Ban a user\n"
            "├ `/unban [user_id]` - Unban a user\n"
            "├ `/banned` - List banned users\n"
            "├ `/warn [user_id] [reason]` - Warn user\n"
            "├ `/warnings [user_id]` - Check warnings\n"
            "└ `/resetwarns [user_id]` - Reset warnings\n\n"
            
            "**⚙️ BOT SETTINGS:**\n"
            "├ `/settings` - View all settings\n"
            "├ `/setwelcome [msg]` - Set welcome message\n"
            "├ `/setgoodbye [msg]` - Set goodbye message\n"
            "├ `/setrules [text]` - Set group rules\n"
            "├ `/setlang [en/bn]` - Change language\n"
            "├ `/setbutton [name] [url]` - Custom button\n"
            "└ `/resetall` - Reset all settings\n\n"
            
            "**🔄 AUTO-MODERATION:**\n"
            "├ `/addfilter [word] [reply]` - Add auto-reply\n"
            "├ `/removefilter [word]` - Remove filter\n"
            "├ `/filters` - List all filters\n"
            "├ `/setantispam [on/off]` - Toggle anti-spam\n"
            "├ `/setlangfilter [on/off]` - Language filter\n"
            "└ `/setwordfilter [word]` - Add blocked word\n\n"
            
            "**📝 USER MANAGEMENT:**\n"
            "├ `/userinfo [user_id]` - User details\n"
            "├ `/usernote [user_id] [note]` - Add user note\n"
            "├ `/usernotes [user_id]` - View user notes\n"
            "├ `/activity [user_id]` - User activity\n"
            "├ `/exportusers` - Export user list\n"
            "└ `/importusers` - Import user list\n\n"
            
            "**💬 GROUP MANAGEMENT:**\n"
            "├ `/groups` - List all groups\n"
            "├ `/leave [chat_id]` - Leave group\n"
            "├ `/setgrouptitle [title]` - Set group title\n"
            "├ `/setgrouppic` - Set group picture\n"
            "├ `/promote [user_id]` - Promote in group\n"
            "└ `/demote [user_id]` - Demote in group\n\n"
            
            "**🔐 SECURITY:**\n"
            "├ `/backup` - Backup database\n"
            "├ `/restore [file]` - Restore database\n"
            "├ `/listbackups` - List backups\n"
            "├ `/cleanup` - Clean old data\n"
            "├ `/optimize` - Optimize database\n"
            "└ `/resetstats` - Reset statistics\n\n"
            
            "**📱 OTHER COMMANDS:**\n"
            "├ `/id` - Get user/chat ID\n"
            "├ `/info` - Bot information\n"
            "├ `/ping` - Check bot status\n"
            "├ `/uptime` - Bot uptime\n"
            "├ `/restart` - Restart bot\n"
            "├ `/shutdown` - Shutdown bot\n"
            "├ `/log` - Get recent logs from group\n"
            "└ `/help` - Show this help menu"
        )
        bot.send_message(chat_id, admin_panel, parse_mode="Markdown")
    else:
        user_panel = (
            "👋 **Welcome to File Store Bot!**\n\n"
            "**Available Commands:**\n"
            "├ `/start` - Start the bot\n"
            "├ `/help` - Show help\n"
            "├ `/about` - About bot\n"
            "├ `/search [query]` - Search files\n"
            "├ `/stats` - Bot statistics\n"
            "└ `/report [issue]` - Report problem\n\n"
            "📌 **How to get files:**\n"
            "1. Click on any file link\n"
            "2. Join all required channels\n"
            "3. Click verify button\n"
            "4. Get your file instantly!"
        )
        bot.send_message(chat_id, user_panel, parse_mode="Markdown")
        update_stat('total_starts')

# --- ADMIN COMMAND: ADD NEW ADMIN ---
@bot.message_handler(commands=['addadmin'])
def add_admin_cmd(message):
    """Add a new admin"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can add new admins.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/addadmin user_id [permissions]`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        permissions = parts[2] if len(parts) > 2 else 'basic'
        
        # Try to get username
        username = ""
        try:
            user = bot.get_chat(user_id)
            username = user.username or ""
        except:
            pass
        
        add_admin(user_id, username, message.chat.id, permissions)
        bot.reply_to(message, f"✅ Admin {user_id} added successfully with permissions: {permissions}")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID.")

# --- ADMIN COMMAND: REMOVE ADMIN ---
@bot.message_handler(commands=['removeadmin'])
def remove_admin_cmd(message):
    """Remove an admin"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can remove admins.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/removeadmin user_id`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        if user_id in SUPER_ADMIN_IDS:
            bot.reply_to(message, "❌ Cannot remove super admin.")
            return
        
        remove_admin(user_id, message.chat.id)
        bot.reply_to(message, f"✅ Admin {user_id} removed successfully.")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID.")

# --- ADMIN COMMAND: LIST ADMINS ---
@bot.message_handler(commands=['admins'])
def list_admins_cmd(message):
    """List all admins"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    admins = get_all_admins()
    msg = "**👑 Admin List:**\n\n"
    msg += "**Super Admins:**\n"
    for sa in SUPER_ADMIN_IDS:
        msg += f"├ `{sa}` (Super Admin)\n"
    
    if admins:
        msg += "\n**Regular Admins:**\n"
        for user_id, username, permissions in admins:
            username_display = f"(@{username})" if username else ""
            msg += f"├ `{user_id}` {username_display} - {permissions}\n"
    else:
        msg += "\nNo regular admins."
    
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# --- ADMIN COMMAND: SET ADMIN PERMISSIONS ---
@bot.message_handler(commands=['setadminperm'])
def set_admin_perm_cmd(message):
    """Set admin permissions"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can set permissions.")
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "❌ Usage: `/setadminperm user_id permissions`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        permissions = parts[2]
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE admins SET permissions=? WHERE user_id=?', (permissions, user_id))
        conn.commit()
        conn.close()
        
        log_to_group("PERMISSIONS UPDATED", message.chat.id, f"User: {user_id}\nNew Permissions: {permissions}")
        bot.reply_to(message, f"✅ Permissions for {user_id} set to: {permissions}")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID.")

# --- ADMIN COMMAND: ADMIN LOG ---
@bot.message_handler(commands=['adminlog'])
def admin_log_cmd(message):
    """View logs for specific admin"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can view admin logs.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/adminlog user_id`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        
        # Get logs from group (this would require storing logs in database)
        # For now, just indicate that logs are in the group
        bot.reply_to(message, f"📋 Check the log group for logs related to user {user_id}")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID.")

# --- ADMIN COMMAND: ADD CHANNEL ---
@bot.message_handler(commands=['add'])
def add_menu_cmd(message):
    """Add a new channel/group to verification list"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    parts = message.text.split()
    if len(parts) >= 3:
        username = parts[-1].replace("@", "").strip()
        button_name = " ".join(parts[1:-1])
        add_extra(username, button_name, message.chat.id)
        bot.reply_to(message, f"✅ @{username} added with button name: '{button_name}'")
    else:
        bot.reply_to(message, "❌ Usage: `/add Join Extra @username`", parse_mode="Markdown")

# --- ADMIN COMMAND: REMOVE CHANNEL ---
@bot.message_handler(commands=['remove'])
def remove_menu_cmd(message):
    """Remove a channel/group from verification list"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    parts = message.text.split()
    if len(parts) > 1:
        username = parts[1].replace("@", "").strip()
        remove_extra(username, message.chat.id)
        bot.reply_to(message, f"🗑️ @{username} has been removed.")
    else:
        bot.reply_to(message, "❌ Usage: `/remove @username`", parse_mode="Markdown")

# --- ADMIN COMMAND: LIST CHANNELS ---
@bot.message_handler(commands=['channels'])
def list_channels(message):
    """List all verification channels"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    extras = get_extra_list()
    msg = "**📋 Verification Channels:**\n\n"
    msg += f"**Fixed Channel:** @{FIXED_CH}\n"
    msg += f"**Fixed Group:** @{FIXED_GR}\n\n"
    
    if extras:
        msg += "**Extra Channels:**\n"
        for username, btn_name in extras:
            msg += f"├ @{username} - `{btn_name}`\n"
    else:
        msg += "No extra channels added."
    
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# --- ADMIN COMMAND: SET FIXED CHANNELS ---
@bot.message_handler(commands=['setfixed'])
def set_fixed_channels(message):
    """Set fixed channels and groups"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can set fixed channels.")
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "❌ Usage: `/setfixed channel group`", parse_mode="Markdown")
        return
    
    global FIXED_CH, FIXED_GR
    old_ch = FIXED_CH
    old_gr = FIXED_GR
    FIXED_CH = parts[1].replace("@", "")
    FIXED_GR = parts[2].replace("@", "")
    
    set_setting('fixed_ch', FIXED_CH)
    set_setting('fixed_gr', FIXED_GR)
    
    log_to_group("FIXED CHANNELS UPDATED", message.chat.id, f"Old: @{old_ch}, @{old_gr}\nNew: @{FIXED_CH}, @{FIXED_GR}")
    bot.reply_to(message, f"✅ Fixed channels updated:\nChannel: @{FIXED_CH}\nGroup: @{FIXED_GR}")

# --- ADMIN COMMAND: CHECK MEMBERSHIP ---
@bot.message_handler(commands=['checkmembership'])
def check_membership(message):
    """Check if a user has joined all channels"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/checkmembership user_id`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        extras = [row[0] for row in get_extra_list()]
        all_to_check = [FIXED_CH, FIXED_GR] + extras
        
        msg = f"**🔍 Membership Check for User `{user_id}`:**\n\n"
        
        for username in all_to_check:
            try:
                status = bot.get_chat_member(f"@{username}", user_id).status
                emoji = "✅" if status in ['member', 'administrator', 'creator'] else "❌"
                msg += f"{emoji} @{username}: {status}\n"
            except Exception as e:
                msg += f"⚠️ @{username}: Error checking\n"
        
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID.")

# --- ADMIN COMMAND: FILE INFO ---
@bot.message_handler(commands=['fileinfo'])
def file_info(message):
    """Get detailed information about a file"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/fileinfo file_key`", parse_mode="Markdown")
        return
    
    key = parts[1]
    f_data = get_file_from_db(key)
    
    if f_data:
        file_id, f_type, caption, downloads = f_data
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT uploaded_by, upload_date FROM files WHERE key=?', (key,))
        result = cursor.fetchone()
        uploaded_by, upload_date = result if result else (0, 0)
        conn.close()
        
        upload_time = datetime.datetime.fromtimestamp(upload_date).strftime("%Y-%m-%d %H:%M:%S")
        
        msg = (
            f"**📁 File Information:**\n\n"
            f"**Key:** `{key}`\n"
            f"**Type:** {f_type}\n"
            f"**Caption:** {caption}\n"
            f"**Downloads:** {downloads}\n"
            f"**Uploaded By:** `{uploaded_by}`\n"
            f"**Upload Date:** {upload_time}\n"
            f"**File ID:** `{file_id}`"
        )
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, f"❌ File `{key}` not found.", parse_mode="Markdown")

# --- ADMIN COMMAND: TOP FILES ---
@bot.message_handler(commands=['topfiles'])
def top_files(message):
    """Show most downloaded files"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    files = get_all_files()
    if not files:
        bot.send_message(message.chat.id, "No files found.")
        return
    
    # Sort by downloads
    sorted_files = sorted(files, key=lambda x: x[3], reverse=True)[:10]
    
    msg = "**🏆 Top 10 Most Downloaded Files:**\n\n"
    for i, (key, f_type, caption, downloads, _) in enumerate(sorted_files, 1):
        short_caption = (caption[:30] + "...") if len(caption) > 30 else caption
        msg += f"{i}. `{key}` - {downloads} downloads\n   {short_caption}\n"
    
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# --- ADMIN COMMAND: SEARCH FILE ---
@bot.message_handler(commands=['searchfile'])
def search_file(message):
    """Search files by caption"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/searchfile query`", parse_mode="Markdown")
        return
    
    query = parts[1].lower()
    files = get_all_files()
    
    results = []
    for key, f_type, caption, downloads, _ in files:
        if query in caption.lower():
            results.append((key, f_type, caption, downloads))
    
    if results:
        msg = f"**🔍 Search Results for '{query}':**\n\n"
        for key, f_type, caption, downloads in results[:10]:
            msg += f"• `{key}` - {f_type}\n  {caption[:50]}\n  Downloads: {downloads}\n\n"
        
        if len(results) > 10:
            msg += f"\n... and {len(results) - 10} more results."
        
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, f"❌ No files found matching '{query}'.")

# --- ADMIN COMMAND: BROADCAST ---
@bot.message_handler(commands=['broadcast'])
def broadcast_to_all(message):
    """Send broadcast message to all users"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Please include a message. Example: `/broadcast Hello everyone`", parse_mode="Markdown")
        return
    
    broadcast_msg = args[1]
    success_count = 0
    failed_count = 0
    
    status_msg = bot.reply_to(message, "🚀 Starting Broadcast...")
    
    for chat_id in list(all_chats):
        try:
            bot.send_message(chat_id, broadcast_msg)
            success_count += 1
            time.sleep(0.05)  # Rate limiting
        except Exception as e:
            failed_count += 1
            continue
    
    result_msg = (
        f"✅ **Broadcast Finished!**\n\n"
        f"📨 **Sent to:** {success_count} users\n"
        f"❌ **Failed:** {failed_count} users\n"
        f"👥 **Total in database:** {len(all_chats)}"
    )
    bot.edit_message_text(result_msg, message.chat.id, status_msg.message_id, parse_mode="Markdown")
    update_stat('total_broadcasts')
    
    # Log to group
    log_broadcast(message.chat.id, success_count, failed_count, broadcast_msg)

# --- ADMIN COMMAND: BROADCAST (FORWARD) ---
@bot.message_handler(commands=['broadcastfwd'])
def broadcast_forward(message):
    """Forward a message to all users"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Please reply to a message to forward.")
        return
    
    success_count = 0
    failed_count = 0
    
    status_msg = bot.reply_to(message, "🚀 Starting Broadcast Forward...")
    
    for chat_id in list(all_chats):
        try:
            bot.forward_message(chat_id, message.chat.id, message.reply_to_message.message_id)
            success_count += 1
            time.sleep(0.05)
        except:
            failed_count += 1
            continue
    
    result_msg = f"✅ Broadcast Forward Finished!\n\n📨 Sent to: {success_count}\n❌ Failed: {failed_count}"
    bot.edit_message_text(result_msg, message.chat.id, status_msg.message_id)
    
    # Log to group
    log_broadcast(message.chat.id, success_count, failed_count, "Forwarded message")

# --- ADMIN COMMAND: SCHEDULE BROADCAST ---
@bot.message_handler(commands=['schedule'])
def schedule_broadcast_cmd(message):
    """Schedule a broadcast for later"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "❌ Usage: `/schedule time message`\nTime format: YYYY-MM-DD HH:MM", parse_mode="Markdown")
        return
    
    try:
        scheduled_time = datetime.datetime.strptime(parts[1], "%Y-%m-%d %H:%M")
        scheduled_timestamp = scheduled_time.timestamp()
        message_text = parts[2]
        
        schedule_broadcast(message_text, scheduled_timestamp, message.chat.id)
        
        log_to_group("BROADCAST SCHEDULED", message.chat.id, f"Time: {parts[1]}\nMessage: {message_text[:100]}")
        bot.reply_to(message, f"✅ Broadcast scheduled for {parts[1]}")
    except ValueError:
        bot.reply_to(message, "❌ Invalid time format. Use: YYYY-MM-DD HH:MM")

# --- ADMIN COMMAND: CANCEL BROADCAST ---
@bot.message_handler(commands=['cancelbroadcast'])
def cancel_broadcast(message):
    """Cancel a scheduled broadcast"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/cancelbroadcast broadcast_id`", parse_mode="Markdown")
        return
    
    try:
        broadcast_id = int(parts[1])
        update_broadcast_status(broadcast_id, 'cancelled')
        log_to_group("BROADCAST CANCELLED", message.chat.id, f"Broadcast ID: {broadcast_id}")
        bot.reply_to(message, f"✅ Broadcast {broadcast_id} cancelled.")
    except:
        bot.reply_to(message, "❌ Invalid broadcast ID.")

# --- ADMIN COMMAND: BROADCAST STATUS ---
@bot.message_handler(commands=['broadcaststatus'])
def broadcast_status(message):
    """Check status of scheduled broadcasts"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, message, scheduled_time, status FROM scheduled_broadcasts ORDER BY scheduled_time')
    rows = cursor.fetchall()
    conn.close()
    
    if rows:
        msg = "**📊 Scheduled Broadcasts:**\n\n"
        current_time = time.time()
        
        for broadcast_id, message_text, scheduled_time, status in rows:
            scheduled_dt = datetime.datetime.fromtimestamp(scheduled_time)
            time_diff = scheduled_dt - datetime.datetime.fromtimestamp(current_time)
            
            if time_diff.total_seconds() > 0:
                time_left = str(time_diff).split('.')[0]
                status_emoji = "⏳" if status == 'pending' else "✅" if status == 'completed' else "❌"
                short_msg = message_text[:30] + "..." if len(message_text) > 30 else message_text
                msg += f"{status_emoji} ID: {broadcast_id}\n   {short_msg}\n   Time: {scheduled_dt}\n   Left: {time_left}\n   Status: {status}\n\n"
        
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "No scheduled broadcasts.")

# --- ADMIN COMMAND: TEST BROADCAST ---
@bot.message_handler(commands=['testbroadcast'])
def test_broadcast(message):
    """Send test broadcast to all admins"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Please include a test message.")
        return
    
    test_msg = parts[1]
    success_count = 0
    
    for admin_id in ADMIN_IDS + SUPER_ADMIN_IDS:
        try:
            bot.send_message(admin_id, f"🧪 **TEST BROADCAST**\n\n{test_msg}", parse_mode="Markdown")
            success_count += 1
        except:
            continue
    
    bot.reply_to(message, f"✅ Test broadcast sent to {success_count} admins.")

# --- ADMIN COMMAND: USER STATISTICS ---
@bot.message_handler(commands=['userstats'])
def user_stats(message):
    """Show detailed user statistics"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    total, active_24h, active_7d = get_user_stats()
    
    # Get new users today
    today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0).timestamp()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM user_activity WHERE last_seen > ?', (today_start,))
    new_today = cursor.fetchone()[0]
    
    # Get user growth
    cursor.execute('''
        SELECT DATE(datetime(last_seen, 'unixepoch')), COUNT(*) 
        FROM user_activity 
        WHERE last_seen > ? 
        GROUP BY DATE(datetime(last_seen, 'unixepoch'))
        ORDER BY DATE(datetime(last_seen, 'unixepoch')) DESC
        LIMIT 7
    ''', (time.time() - 604800,))
    daily_activity = cursor.fetchall()
    conn.close()
    
    msg = (
        "**📊 User Statistics:**\n\n"
        f"**Total Users:** {total}\n"
        f"**Active Today:** {active_24h}\n"
        f"**Active This Week:** {active_7d}\n"
        f"**New Today:** {new_today}\n\n"
        "**Daily Activity (Last 7 Days):**\n"
    )
    
    for date, count in daily_activity:
        msg += f"├ {date}: {count} users\n"
    
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# --- ADMIN COMMAND: FILE STATISTICS ---
@bot.message_handler(commands=['filestats'])
def file_stats(message):
    """Show file statistics"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    files = get_all_files()
    total_files = len(files)
    total_downloads = sum(f[3] for f in files)
    
    # Get file types breakdown
    file_types = {}
    for _, f_type, _, _, _ in files:
        file_types[f_type] = file_types.get(f_type, 0) + 1
    
    msg = (
        "**📁 File Statistics:**\n\n"
        f"**Total Files:** {total_files}\n"
        f"**Total Downloads:** {total_downloads}\n"
        f"**Average Downloads/File:** {total_downloads/total_files if total_files > 0 else 0:.1f}\n\n"
        "**File Types:**\n"
    )
    
    for f_type, count in file_types.items():
        percentage = (count / total_files * 100) if total_files > 0 else 0
        msg += f"├ {f_type}: {count} ({percentage:.1f}%)\n"
    
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# --- ADMIN COMMAND: GROUP STATISTICS ---
@bot.message_handler(commands=['groupstats'])
def group_stats(message):
    """Show group statistics"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    groups = get_all_groups()
    total_groups = len(groups)
    
    msg = "**💬 Group Statistics:**\n\n"
    msg += f"**Total Groups:** {total_groups}\n\n"
    
    if groups:
        msg += "**Recent Groups:**\n"
        for chat_id, title, username, added_date in groups[:10]:
            added_dt = datetime.datetime.fromtimestamp(added_date).strftime("%Y-%m-%d")
            username_display = f"(@{username})" if username else ""
            msg += f"├ {title} {username_display}\n   ID: `{chat_id}` - Added: {added_dt}\n"
    
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# --- ADMIN COMMAND: COMMAND STATISTICS ---
@bot.message_handler(commands=['commandstats'])
def command_stats_cmd(message):
    """Show command usage statistics"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    cmd_stats = get_command_stats()
    
    msg = "**📊 Command Usage Statistics:**\n\n"
    total_commands = sum(count for _, count in cmd_stats)
    msg += f"**Total Commands:** {total_commands}\n\n"
    
    for cmd, count in cmd_stats[:15]:
        percentage = (count / total_commands * 100) if total_commands > 0 else 0
        bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))
        msg += f"`{cmd}`: {count} ({percentage:.1f}%)\n{bar}\n"
    
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# --- ADMIN COMMAND: HOURLY STATISTICS ---
@bot.message_handler(commands=['hourlystats'])
def hourly_stats(message):
    """Show hourly activity statistics"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT strftime('%H', datetime(access_time, 'unixepoch')), COUNT(*) 
        FROM file_access_log 
        WHERE access_time > ? 
        GROUP BY strftime('%H', datetime(access_time, 'unixepoch'))
        ORDER BY strftime('%H', datetime(access_time, 'unixepoch'))
    ''', (time.time() - 604800,))
    hourly_data = cursor.fetchall()
    conn.close()
    
    msg = "**⏰ Hourly Activity (Last 7 Days):**\n\n"
    
    if hourly_data:
        max_count = max(count for _, count in hourly_data)
        
        for hour, count in hourly_data:
            hour_int = int(hour)
            hour_display = f"{hour_int:02d}:00 - {hour_int:02d}:59"
            bar_length = int((count / max_count) * 20) if max_count > 0 else 0
            bar = "█" * bar_length
            msg += f"{hour_display}: {bar} {count}\n"
    else:
        msg += "No activity data available."
    
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# --- ADMIN COMMAND: WARN USER ---
@bot.message_handler(commands=['warn'])
def warn_user(message):
    """Warn a user"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/warn user_id [reason]`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        reason = parts[2] if len(parts) > 2 else "No reason provided"
        
        # Create warnings table if not exists
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_warnings (
            user_id INTEGER PRIMARY KEY,
            warning_count INTEGER DEFAULT 0,
            last_warn_reason TEXT,
            last_warn_time TIMESTAMP,
            warned_by INTEGER
        )''')
        
        cursor.execute('''INSERT INTO user_warnings 
                          (user_id, warning_count, last_warn_reason, last_warn_time, warned_by) 
                          VALUES (?, 1, ?, ?, ?)
                          ON CONFLICT(user_id) DO UPDATE SET 
                          warning_count = warning_count + 1,
                          last_warn_reason = excluded.last_warn_reason,
                          last_warn_time = excluded.last_warn_time,
                          warned_by = excluded.warned_by''',
                       (user_id, reason, time.time(), message.chat.id))
        cursor.execute('SELECT warning_count FROM user_warnings WHERE user_id=?', (user_id,))
        warning_count = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        # Log to group
        log_to_group("USER WARNED", message.chat.id, f"User: {user_id}\nWarning: {warning_count}/3\nReason: {reason}")
        
        # Auto-ban after 3 warnings
        if warning_count >= 3:
            ban_user(user_id, f"Auto-ban after {warning_count} warnings", message.chat.id)
            bot.reply_to(message, f"⚠️ User {user_id} has been auto-banned after {warning_count} warnings.")
        else:
            bot.reply_to(message, f"⚠️ User {user_id} warned ({warning_count}/3).\nReason: {reason}")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID.")

# --- ADMIN COMMAND: CHECK WARNINGS ---
@bot.message_handler(commands=['warnings'])
def check_warnings(message):
    """Check user warnings"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/warnings user_id`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT warning_count, last_warn_reason, last_warn_time, warned_by FROM user_warnings WHERE user_id=?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            warning_count, reason, warn_time, warned_by = row
            warn_dt = datetime.datetime.fromtimestamp(warn_time).strftime("%Y-%m-%d %H:%M:%S")
            
            msg = (
                f"**⚠️ Warnings for User {user_id}:**\n\n"
                f"**Total Warnings:** {warning_count}/3\n"
                f"**Last Warning:** {reason}\n"
                f"**Last Warning Time:** {warn_dt}\n"
                f"**Warned By:** `{warned_by}`"
            )
        else:
            msg = f"✅ User {user_id} has no warnings."
        
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID.")

# --- ADMIN COMMAND: RESET WARNINGS ---
@bot.message_handler(commands=['resetwarns'])
def reset_warnings(message):
    """Reset user warnings"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/resetwarns user_id`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user_warnings WHERE user_id=?', (user_id,))
        conn.commit()
        conn.close()
        
        log_to_group("WARNINGS RESET", message.chat.id, f"User: {user_id}")
        bot.reply_to(message, f"✅ Warnings reset for user {user_id}.")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID.")

# --- ADMIN COMMAND: BAN USER ---
@bot.message_handler(commands=['ban'])
def ban_user_cmd(message):
    """Ban a user from using the bot"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/ban user_id [reason]`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        reason = parts[2] if len(parts) > 2 else "No reason provided"
        
        ban_user(user_id, reason, message.chat.id)
        bot.reply_to(message, f"✅ User `{user_id}` has been banned.\nReason: {reason}", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID. Please provide a numeric ID.")

# --- ADMIN COMMAND: UNBAN USER ---
@bot.message_handler(commands=['unban'])
def unban_user_cmd(message):
    """Unban a user"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/unban user_id`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        unban_user(user_id, message.chat.id)
        bot.reply_to(message, f"✅ User `{user_id}` has been unbanned.", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID. Please provide a numeric ID.")

# --- ADMIN COMMAND: LIST BANNED USERS ---
@bot.message_handler(commands=['banned'])
def list_banned(message):
    """List all banned users"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    banned = get_banned_users()
    if not banned:
        bot.send_message(message.chat.id, "✅ No banned users.")
        return
    
    msg = "**🚫 Banned Users:**\n\n"
    for user_id, reason, banned_at, banned_by in banned:
        date = datetime.datetime.fromtimestamp(banned_at).strftime("%Y-%m-%d %H:%M")
        msg += f"• `{user_id}`\n  Reason: {reason}\n  Banned: {date}\n  By: `{banned_by}`\n\n"
    
    # Split message if too long
    if len(msg) > 4000:
        for i in range(0, len(msg), 4000):
            bot.send_message(message.chat.id, msg[i:i+4000], parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# --- ADMIN COMMAND: SETTINGS ---
@bot.message_handler(commands=['settings'])
def view_settings(message):
    """View all bot settings"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    # Get all settings
    settings = {}
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT setting_key, setting_value FROM bot_settings')
    for key, value in cursor.fetchall():
        settings[key] = value
    conn.close()
    
    msg = "**⚙️ Bot Settings:**\n\n"
    
    # Display settings with emojis
    msg += f"**Fixed Channel:** @{FIXED_CH}\n"
    msg += f"**Fixed Group:** @{FIXED_GR}\n"
    msg += f"**Welcome Message:** {settings.get('welcome_message', 'Not set')[:50]}\n"
    msg += f"**Goodbye Message:** {settings.get('goodbye_message', 'Not set')[:50]}\n"
    msg += f"**Group Rules:** {settings.get('group_rules', 'Not set')[:50]}\n"
    msg += f"**Language:** {settings.get('language', 'en')}\n"
    msg += f"**Anti-Spam:** {settings.get('antispam', 'off')}\n"
    msg += f"**Language Filter:** {settings.get('lang_filter', 'off')}\n"
    
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

# --- ADMIN COMMAND: SET WELCOME ---
@bot.message_handler(commands=['setwelcome'])
def set_welcome(message):
    """Set welcome message for groups"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/setwelcome Welcome message here`\nUse {name} for user's name.", parse_mode="Markdown")
        return
    
    welcome_msg = parts[1]
    chat_id = message.chat.id
    
    if message.chat.type in ['group', 'supergroup']:
        set_setting(f"welcome_{chat_id}", welcome_msg)
        log_to_group("WELCOME MESSAGE SET", message.chat.id, f"Group: {message.chat.title}\nMessage: {welcome_msg[:100]}")
        bot.reply_to(message, f"✅ Welcome message set for this group:\n\n{welcome_msg}")
    else:
        bot.reply_to(message, "❌ This command only works in groups.")

# --- ADMIN COMMAND: SET GOODBYE ---
@bot.message_handler(commands=['setgoodbye'])
def set_goodbye(message):
    """Set goodbye message for groups"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/setgoodbye Goodbye message here`\nUse {name} for user's name.", parse_mode="Markdown")
        return
    
    goodbye_msg = parts[1]
    chat_id = message.chat.id
    
    if message.chat.type in ['group', 'supergroup']:
        set_setting(f"goodbye_{chat_id}", goodbye_msg)
        log_to_group("GOODBYE MESSAGE SET", message.chat.id, f"Group: {message.chat.title}\nMessage: {goodbye_msg[:100]}")
        bot.reply_to(message, f"✅ Goodbye message set for this group:\n\n{goodbye_msg}")
    else:
        bot.reply_to(message, "❌ This command only works in groups.")

# --- ADMIN COMMAND: SET RULES ---
@bot.message_handler(commands=['setrules'])
def set_rules(message):
    """Set rules for group"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/setrules Group rules here`", parse_mode="Markdown")
        return
    
    rules = parts[1]
    chat_id = message.chat.id
    
    if message.chat.type in ['group', 'supergroup']:
        set_setting(f"rules_{chat_id}", rules)
        log_to_group("RULES SET", message.chat.id, f"Group: {message.chat.title}\nRules: {rules[:100]}")
        bot.reply_to(message, f"✅ Rules set for this group:\n\n{rules}")
    else:
        bot.reply_to(message, "❌ This command only works in groups.")

# --- ADMIN COMMAND: SET LANGUAGE ---
@bot.message_handler(commands=['setlang'])
def set_language(message):
    """Set bot language"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/setlang en/bn`", parse_mode="Markdown")
        return
    
    lang = parts[1].lower()
    if lang in ['en', 'bn']:
        set_setting('language', lang)
        log_to_group("LANGUAGE CHANGED", message.chat.id, f"New Language: {lang}")
        bot.reply_to(message, f"✅ Language set to {'English' if lang == 'en' else 'Bangla'}")
    else:
        bot.reply_to(message, "❌ Supported languages: en, bn")

# --- ADMIN COMMAND: SET BUTTON ---
@bot.message_handler(commands=['setbutton'])
def set_button(message):
    """Add custom button"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "❌ Usage: `/setbutton Button Name url`", parse_mode="Markdown")
        return
    
    button_name = parts[1]
    url = parts[2]
    
    # Store in database
    set_setting(f"custom_button_{button_name}", url)
    log_to_group("CUSTOM BUTTON ADDED", message.chat.id, f"Button: {button_name}\nURL: {url}")
    bot.reply_to(message, f"✅ Custom button added: {button_name}")

# --- ADMIN COMMAND: RESET ALL ---
@bot.message_handler(commands=['resetall'])
def reset_all(message):
    """Reset all settings"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can reset all settings.")
        return
    
    # Confirm with keyboard
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Yes, Reset Everything", callback_data="confirm_reset"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_reset")
    )
    
    bot.send_message(
        message.chat.id,
        "⚠️ **WARNING!**\n\nThis will reset ALL settings and delete ALL data!\nAre you sure?",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# --- ADMIN COMMAND: ADD FILTER ---
@bot.message_handler(commands=['addfilter'])
def add_filter_cmd(message):
    """Add an auto-reply filter"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "❌ Usage: `/addfilter keyword reply_message`", parse_mode="Markdown")
        return
    
    keyword = parts[1].lower()
    response = parts[2]
    
    add_filter(keyword, response, 'text', message.chat.id)
    bot.reply_to(message, f"✅ Filter added for keyword: {keyword}")

# --- ADMIN COMMAND: REMOVE FILTER ---
@bot.message_handler(commands=['removefilter'])
def remove_filter_cmd(message):
    """Remove a filter"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/removefilter keyword`", parse_mode="Markdown")
        return
    
    keyword = parts[1].lower()
    remove_filter(keyword, message.chat.id)
    bot.reply_to(message, f"✅ Filter removed for keyword: {keyword}")

# --- ADMIN COMMAND: LIST FILTERS ---
@bot.message_handler(commands=['filters'])
def list_filters(message):
    """List all filters"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    filters = get_all_filters()
    
    if filters:
        msg = "**🔍 Active Filters:**\n\n"
        for keyword, response, response_type in filters:
            short_response = (response[:30] + "...") if len(response) > 30 else response
            msg += f"• `{keyword}` → {short_response} ({response_type})\n"
        
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "No filters active.")

# --- ADMIN COMMAND: SET ANTI-SPAM ---
@bot.message_handler(commands=['setantispam'])
def set_antispam(message):
    """Toggle anti-spam"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        current = get_setting('antispam', 'off')
        bot.reply_to(message, f"❌ Usage: `/setantispam on/off`\nCurrent: {current}", parse_mode="Markdown")
        return
    
    value = parts[1].lower()
    if value in ['on', 'off']:
        set_setting('antispam', value)
        log_to_group("ANTI-SPAM TOGGLED", message.chat.id, f"New Status: {value}")
        bot.reply_to(message, f"✅ Anti-spam turned {value}")
    else:
        bot.reply_to(message, "❌ Use 'on' or 'off'")

# --- ADMIN COMMAND: SET LANGUAGE FILTER ---
@bot.message_handler(commands=['setlangfilter'])
def set_lang_filter(message):
    """Toggle language filter"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        current = get_setting('lang_filter', 'off')
        bot.reply_to(message, f"❌ Usage: `/setlangfilter on/off`\nCurrent: {current}", parse_mode="Markdown")
        return
    
    value = parts[1].lower()
    if value in ['on', 'off']:
        set_setting('lang_filter', value)
        log_to_group("LANGUAGE FILTER TOGGLED", message.chat.id, f"New Status: {value}")
        bot.reply_to(message, f"✅ Language filter turned {value}")
    else:
        bot.reply_to(message, "❌ Use 'on' or 'off'")

# --- ADMIN COMMAND: SET WORD FILTER ---
@bot.message_handler(commands=['setwordfilter'])
def set_word_filter(message):
    """Add a word to filter"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/setwordfilter badword`", parse_mode="Markdown")
        return
    
    word = parts[1].lower()
    
    # Get existing filtered words
    filtered_words = get_setting('filtered_words', '')
    if filtered_words:
        words_list = filtered_words.split(',')
        if word not in words_list:
            words_list.append(word)
            set_setting('filtered_words', ','.join(words_list))
    else:
        set_setting('filtered_words', word)
    
    log_to_group("WORD FILTER ADDED", message.chat.id, f"Word: {word}")
    bot.reply_to(message, f"✅ Added '{word}' to filtered words list.")

# --- ADMIN COMMAND: USER INFO ---
@bot.message_handler(commands=['userinfo'])
def user_info(message):
    """Get detailed user information"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/userinfo user_id`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        
        # Get user info from Telegram
        try:
            user = bot.get_chat(user_id)
            username = f"@{user.username}" if user.username else "No username"
            first_name = user.first_name or ""
            last_name = user.last_name or ""
        except:
            username = "Unknown"
            first_name = "Unknown"
            last_name = ""
        
        # Get database info
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # User activity
        cursor.execute('SELECT last_seen, total_requests FROM user_activity WHERE user_id=?', (user_id,))
        activity = cursor.fetchone()
        
        # File access count
        cursor.execute('SELECT COUNT(*) FROM file_access_log WHERE user_id=? AND success=1', (user_id,))
        successful_downloads = cursor.fetchone()[0]
        
        # Check if banned
        cursor.execute('SELECT reason, banned_at FROM banned_users WHERE user_id=?', (user_id,))
        banned_info = cursor.fetchone()
        
        # Warnings
        cursor.execute('SELECT warning_count FROM user_warnings WHERE user_id=?', (user_id,))
        warning_row = cursor.fetchone()
        warnings = warning_row[0] if warning_row else 0
        
        conn.close()
        
        # Build message
        msg = (
            f"**👤 User Information:**\n\n"
            f"**User ID:** `{user_id}`\n"
            f"**Username:** {username}\n"
            f"**Name:** {first_name} {last_name}\n\n"
            f"**📊 Activity:**\n"
        )
        
        if activity:
            last_seen = datetime.datetime.fromtimestamp(activity[0]).strftime("%Y-%m-%d %H:%M:%S")
            msg += f"• Last Seen: {last_seen}\n"
            msg += f"• Total Requests: {activity[1]}\n"
        else:
            msg += "• Never interacted with bot\n"
        
        msg += f"• Successful Downloads: {successful_downloads}\n"
        msg += f"• Warnings: {warnings}/3\n"
        
        if banned_info:
            reason, banned_at = banned_info
            ban_date = datetime.datetime.fromtimestamp(banned_at).strftime("%Y-%m-%d %H:%M:%S")
            msg += f"\n**🚫 Banned**\n• Reason: {reason}\n• Date: {ban_date}"
        
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID.")

# --- ADMIN COMMAND: ADD USER NOTE ---
@bot.message_handler(commands=['usernote'])
def add_user_note_cmd(message):
    """Add a note about a user"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "❌ Usage: `/usernote user_id note`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        note = parts[2]
        
        add_user_note(user_id, note, message.chat.id)
        log_to_group("USER NOTE ADDED", message.chat.id, f"User: {user_id}\nNote: {note[:100]}")
        bot.reply_to(message, f"✅ Note added for user {user_id}")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID.")

# --- ADMIN COMMAND: VIEW USER NOTES ---
@bot.message_handler(commands=['usernotes'])
def view_user_notes(message):
    """View notes about a user"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/usernotes user_id`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        notes = get_user_notes(user_id)
        
        if notes:
            msg = f"**📝 Notes for User {user_id}:**\n\n"
            for note, created_by, created_at in notes:
                date = datetime.datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M")
                msg += f"• {note}\n  By: `{created_by}` on {date}\n\n"
            
            # Split if too long
            if len(msg) > 4000:
                for i in range(0, len(msg), 4000):
                    bot.send_message(message.chat.id, msg[i:i+4000], parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, f"No notes found for user {user_id}.")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID.")

# --- ADMIN COMMAND: USER ACTIVITY ---
@bot.message_handler(commands=['activity'])
def user_activity(message):
    """Show user activity history"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/activity user_id`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get file access history
        cursor.execute('''SELECT file_key, access_time, success FROM file_access_log 
                          WHERE user_id=? ORDER BY access_time DESC LIMIT 20''', (user_id,))
        access_history = cursor.fetchall()
        
        conn.close()
        
        msg = f"**📊 Activity History for User {user_id}:**\n\n"
        
        if access_history:
            msg += "**Recent File Access:**\n"
            for file_key, access_time, success in access_history:
                date = datetime.datetime.fromtimestamp(access_time).strftime("%Y-%m-%d %H:%M")
                status = "✅" if success else "❌"
                msg += f"{status} `{file_key}` - {date}\n"
        else:
            msg += "No file access history.\n"
        
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "❌ Invalid user ID.")

# --- ADMIN COMMAND: EXPORT USERS ---
@bot.message_handler(commands=['exportusers'])
def export_users(message):
    """Export user list to file"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, first_name, last_seen, total_requests FROM user_activity')
    users = cursor.fetchall()
    conn.close()
    
    if users:
        filename = f"users_export_{int(time.time())}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("User ID,Username,Name,Last Seen,Total Requests\n")
            for user_id, username, first_name, last_seen, total_requests in users:
                date = datetime.datetime.fromtimestamp(last_seen).strftime("%Y-%m-%d %H:%M")
                f.write(f"{user_id},{username or ''},{first_name or ''},{date},{total_requests}\n")
        
        with open(filename, "rb") as f:
            bot.send_document(message.chat.id, f, caption=f"📊 User Export - {len(users)} users")
        
        os.remove(filename)
        log_to_group("USERS EXPORTED", message.chat.id, f"Exported {len(users)} users")
    else:
        bot.send_message(message.chat.id, "No users found.")

# --- ADMIN COMMAND: IMPORT USERS ---
@bot.message_handler(commands=['importusers'])
def import_users(message):
    """Import users from file"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    if not message.reply_to_message or not message.reply_to_message.document:
        bot.reply_to(message, "❌ Please reply to a user list file to import.")
        return
    
    # Download file
    file_info = bot.get_file(message.reply_to_message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    filename = f"import_{int(time.time())}.txt"
    with open(filename, "wb") as f:
        f.write(downloaded_file)
    
    # Process import
    imported = 0
    with open(filename, "r", encoding="utf-8") as f:
        next(f)  # Skip header
        for line in f:
            try:
                parts = line.strip().split(',')
                if len(parts) >= 1:
                    user_id = int(parts[0])
                    all_chats.add(user_id)
                    imported += 1
            except:
                continue
    
    # Update chats file
    with open(CHATS_FILE, "w") as f:
        for chat_id in all_chats:
            f.write(f"{chat_id}\n")
    
    os.remove(filename)
    log_to_group("USERS IMPORTED", message.chat.id, f"Imported {imported} users")
    bot.reply_to(message, f"✅ Imported {imported} users.")

# --- ADMIN COMMAND: GROUPS ---
@bot.message_handler(commands=['groups'])
def list_groups(message):
    """List all groups where bot is added"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    groups = get_all_groups()
    
    if groups:
        msg = "**💬 Groups where bot is added:**\n\n"
        for chat_id, title, username, added_date in groups:
            date = datetime.datetime.fromtimestamp(added_date).strftime("%Y-%m-%d")
            username_display = f"(@{username})" if username else ""
            msg += f"• {title} {username_display}\n  ID: `{chat_id}` - Added: {date}\n\n"
        
        # Split if too long
        if len(msg) > 4000:
            for i in range(0, len(msg), 4000):
                bot.send_message(message.chat.id, msg[i:i+4000], parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "Bot is not added to any groups.")

# --- ADMIN COMMAND: LEAVE GROUP ---
@bot.message_handler(commands=['leave'])
def leave_group(message):
    """Make bot leave a group"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    parts = message.text.split()
    if len(parts) > 1:
        try:
            chat_id = int(parts[1])
            # Get chat info before leaving
            try:
                chat = bot.get_chat(chat_id)
                chat_title = chat.title or "Unknown"
            except:
                chat_title = "Unknown"
            
            bot.send_message(chat_id, "👋 Goodbye! Leaving this group as per admin request...")
            bot.leave_chat(chat_id)
            remove_group(chat_id, chat_title)
            log_to_group("BOT LEFT GROUP", message.chat.id, f"Group: {chat_title}\nID: {chat_id}")
            bot.reply_to(message, f"✅ Left group {chat_id}")
        except:
            bot.reply_to(message, "❌ Failed to leave group.")
    elif message.chat.type in ['group', 'supergroup']:
        chat_title = message.chat.title or "Unknown"
        bot.send_message(message.chat.id, "👋 Goodbye! Leaving this group...")
        bot.leave_chat(message.chat.id)
        remove_group(message.chat.id, chat_title)
        log_to_group("BOT LEFT GROUP", message.chat.id, f"Group: {chat_title}\nID: {message.chat.id}")
    else:
        bot.reply_to(message, "❌ Usage: `/leave [chat_id]`", parse_mode="Markdown")

# --- ADMIN COMMAND: SET GROUP TITLE ---
@bot.message_handler(commands=['setgrouptitle'])
def set_group_title(message):
    """Set group title"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ This command only works in groups.")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/setgrouptitle New Title`", parse_mode="Markdown")
        return
    
    new_title = parts[1]
    old_title = message.chat.title
    
    try:
        bot.set_chat_title(message.chat.id, new_title)
        log_to_group("GROUP TITLE CHANGED", message.chat.id, f"Group: {old_title}\nNew Title: {new_title}")
        bot.reply_to(message, f"✅ Group title changed to: {new_title}")
    except:
        bot.reply_to(message, "❌ Failed to change title. Make sure I'm an admin.")

# --- ADMIN COMMAND: SET GROUP PICTURE ---
@bot.message_handler(commands=['setgrouppic'])
def set_group_pic(message):
    """Set group picture"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ This command only works in groups.")
        return
    
    if not message.reply_to_message or not message.reply_to_message.photo:
        bot.reply_to(message, "❌ Please reply to a photo to set as group picture.")
        return
    
    photo = message.reply_to_message.photo[-1]
    file_info = bot.get_file(photo.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    try:
        bot.set_chat_photo(message.chat.id, downloaded_file)
        log_to_group("GROUP PICTURE CHANGED", message.chat.id, f"Group: {message.chat.title}")
        bot.reply_to(message, "✅ Group picture updated successfully!")
    except:
        bot.reply_to(message, "❌ Failed to set picture. Make sure I'm an admin.")

# --- ADMIN COMMAND: PROMOTE ---
@bot.message_handler(commands=['promote'])
def promote_user(message):
    """Promote user in group"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ This command only works in groups.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/promote user_id`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        
        bot.promote_chat_member(
            message.chat.id,
            user_id,
            can_change_info=True,
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_promote_members=False
        )
        
        log_to_group("USER PROMOTED", message.chat.id, f"Group: {message.chat.title}\nPromoted User: {user_id}")
        bot.reply_to(message, f"✅ User {user_id} promoted to admin!")
    except:
        bot.reply_to(message, "❌ Failed to promote. Make sure I'm an admin.")

# --- ADMIN COMMAND: DEMOTE ---
@bot.message_handler(commands=['demote'])
def demote_user(message):
    """Demote user in group"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    if message.chat.type not in ['group', 'supergroup']:
        bot.reply_to(message, "❌ This command only works in groups.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/demote user_id`", parse_mode="Markdown")
        return
    
    try:
        user_id = int(parts[1])
        
        bot.promote_chat_member(
            message.chat.id,
            user_id,
            can_change_info=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False
        )
        
        log_to_group("USER DEMOTED", message.chat.id, f"Group: {message.chat.title}\nDemoted User: {user_id}")
        bot.reply_to(message, f"✅ User {user_id} demoted!")
    except:
        bot.reply_to(message, "❌ Failed to demote. Make sure I'm an admin.")

# --- ADMIN COMMAND: BACKUP ---
@bot.message_handler(commands=['backup'])
def backup_database_cmd(message):
    """Create database backup"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can create backups.")
        return
    
    status_msg = bot.reply_to(message, "🔄 Creating backup...")
    
    backup_file = backup_database()
    
    if os.path.exists(backup_file):
        with open(backup_file, "rb") as f:
            bot.send_document(
                message.chat.id,
                f,
                caption=f"✅ Database Backup - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        bot.delete_message(message.chat.id, status_msg.message_id)
        log_to_group("DATABASE BACKUP", message.chat.id, f"Backup created: {backup_file}")
    else:
        bot.edit_message_text("❌ Backup failed.", message.chat.id, status_msg.message_id)

# --- ADMIN COMMAND: RESTORE ---
@bot.message_handler(commands=['restore'])
def restore_database_cmd(message):
    """Restore database from backup"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can restore backups.")
        return
    
    if not message.reply_to_message or not message.reply_to_message.document:
        bot.reply_to(message, "❌ Please reply to a backup file to restore.")
        return
    
    # Download backup file
    file_info = bot.get_file(message.reply_to_message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    filename = f"restore_{int(time.time())}.db"
    with open(filename, "wb") as f:
        f.write(downloaded_file)
    
    # Restore
    if restore_database(filename):
        log_to_group("DATABASE RESTORED", message.chat.id, "Database restored from backup")
        bot.reply_to(message, "✅ Database restored successfully! Restarting bot...")
        os.remove(filename)
        os._exit(0)  # Restart bot
    else:
        bot.reply_to(message, "❌ Failed to restore database.")
        os.remove(filename)

# --- ADMIN COMMAND: LIST BACKUPS ---
@bot.message_handler(commands=['listbackups'])
def list_backups(message):
    """List available backups"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can view backups.")
        return
    
    backups = get_backup_files()
    
    if backups:
        msg = "**📋 Available Backups:**\n\n"
        for backup in backups[:20]:
            file_path = os.path.join(BACKUP_DIR, backup)
            size = os.path.getsize(file_path) / 1024  # KB
            modified = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M")
            msg += f"• {backup}\n  Size: {size:.1f} KB - Modified: {modified}\n"
        
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "No backups found.")

# --- ADMIN COMMAND: CLEANUP ---
@bot.message_handler(commands=['cleanup'])
def cleanup_data(message):
    """Clean old data"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can cleanup data.")
        return
    
    cutoff_time = time.time() - (30 * 24 * 60 * 60)  # 30 days
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Delete old access logs
    cursor.execute('DELETE FROM file_access_log WHERE access_time < ?', (cutoff_time,))
    logs_deleted = cursor.rowcount
    
    # Delete old user activity
    cursor.execute('DELETE FROM user_activity WHERE last_seen < ?', (cutoff_time,))
    activity_deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    log_to_group("DATA CLEANUP", message.chat.id, f"Logs deleted: {logs_deleted}\nInactive users removed: {activity_deleted}")
    bot.reply_to(
        message,
        f"✅ Cleanup completed!\n\n"
        f"• Old logs deleted: {logs_deleted}\n"
        f"• Inactive users removed: {activity_deleted}"
    )

# --- ADMIN COMMAND: OPTIMIZE ---
@bot.message_handler(commands=['optimize'])
def optimize_database(message):
    """Optimize database"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can optimize database.")
        return
    
    status_msg = bot.reply_to(message, "🔄 Optimizing database...")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('VACUUM')
    conn.close()
    
    log_to_group("DATABASE OPTIMIZED", message.chat.id, "Database vacuum completed")
    bot.edit_message_text("✅ Database optimized successfully!", message.chat.id, status_msg.message_id)

# --- ADMIN COMMAND: RESET STATS ---
@bot.message_handler(commands=['resetstats'])
def reset_stats(message):
    """Reset all statistics"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can reset stats.")
        return
    
    # Confirm with keyboard
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Yes, Reset Stats", callback_data="confirm_reset_stats"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_reset_stats")
    )
    
    bot.send_message(
        message.chat.id,
        "⚠️ **Warning!**\n\nThis will reset ALL statistics!\nAre you sure?",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# --- ADMIN COMMAND: ID ---
@bot.message_handler(commands=['id'])
def get_id(message):
    """Get user/chat ID"""
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        username = message.reply_to_message.from_user.username or "No username"
        first_name = message.reply_to_message.from_user.first_name or ""
        
        msg = (
            f"**👤 User Info:**\n"
            f"**ID:** `{user_id}`\n"
            f"**Username:** @{username}\n"
            f"**Name:** {first_name}\n"
        )
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        msg = (
            f"**📱 Chat Info:**\n"
            f"**Chat ID:** `{message.chat.id}`\n"
            f"**Chat Type:** {message.chat.type}\n"
            f"**Chat Title:** {message.chat.title or 'N/A'}"
        )
        bot.reply_to(message, msg, parse_mode="Markdown")

# --- ADMIN COMMAND: INFO ---
@bot.message_handler(commands=['info'])
def bot_info(message):
    """Show bot information"""
    me = bot.get_me()
    
    uptime_seconds = time.time() - bot_start_time if 'bot_start_time' in globals() else 0
    uptime = str(datetime.timedelta(seconds=int(uptime_seconds)))
    
    total_users = get_stat('total_users')
    total_files = len(get_all_files())
    total_downloads = get_stat('total_file_requests')
    
    msg = (
        f"**🤖 Bot Information**\n\n"
        f"**Bot Name:** {me.first_name}\n"
        f"**Username:** @{me.username}\n"
        f"**Bot ID:** `{me.id}`\n\n"
        f"**📊 Statistics:**\n"
        f"• Total Users: {total_users}\n"
        f"• Total Files: {total_files}\n"
        f"• Total Downloads: {total_downloads}\n"
        f"• Uptime: {uptime}\n\n"
        f"**⚙️ System:**\n"
        f"• Python: {os.sys.version.split()[0]}\n"
        f"• PyTelegramBotAPI: {telebot.__version__}\n"
        f"• Database: SQLite3"
    )
    
    bot.reply_to(message, msg, parse_mode="Markdown")

# --- ADMIN COMMAND: PING ---
@bot.message_handler(commands=['ping'])
def ping(message):
    """Check bot status"""
    import time
    start_time = time.time()
    msg = bot.reply_to(message, "🏓 Pinging...")
    end_time = time.time()
    
    response_time = (end_time - start_time) * 1000
    bot.edit_message_text(
        f"🏓 **Pong!**\nResponse Time: `{response_time:.2f}ms`\nStatus: ✅ Online",
        message.chat.id,
        msg.message_id,
        parse_mode="Markdown"
    )

# --- ADMIN COMMAND: UPTIME ---
bot_start_time = time.time()

@bot.message_handler(commands=['uptime'])
def uptime(message):
    """Show bot uptime"""
    uptime_seconds = time.time() - bot_start_time
    uptime_string = str(datetime.timedelta(seconds=int(uptime_seconds)))
    
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    
    msg = (
        f"**⏱️ Bot Uptime**\n\n"
        f"**Total:** {uptime_string}\n"
        f"**Breakdown:**\n"
        f"• Days: {int(days)}\n"
        f"• Hours: {int(hours)}\n"
        f"• Minutes: {int(minutes)}\n"
        f"• Seconds: {int(seconds)}"
    )
    
    bot.reply_to(message, msg, parse_mode="Markdown")

# --- ADMIN COMMAND: LOG ---
@bot.message_handler(commands=['log'])
def get_log(message):
    """Get recent logs from log group"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can view logs.")
        return
    
    parts = message.text.split()
    limit = 10
    if len(parts) > 1:
        try:
            limit = int(parts[1])
            if limit > 50:
                limit = 50
        except:
            pass
    
    bot.reply_to(message, f"📋 Please check the log group (@{LOG_GROUP_ID}) for the last {limit} messages.")

# --- ADMIN COMMAND: RESTART ---
@bot.message_handler(commands=['restart'])
def restart_bot(message):
    """Restart the bot"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can restart the bot.")
        return
    
    log_system_event("BOT RESTARTING", f"Restarted by {message.chat.id}")
    bot.reply_to(message, "🔄 Restarting bot...")
    os._exit(0)  # This will restart the bot if run with a process manager

# --- ADMIN COMMAND: SHUTDOWN ---
@bot.message_handler(commands=['shutdown'])
def shutdown_bot(message):
    """Shutdown the bot"""
    if not is_super_admin(message.chat.id):
        bot.reply_to(message, "❌ Only super admins can shutdown the bot.")
        return
    
    log_system_event("BOT SHUTDOWN", f"Shut down by {message.chat.id}")
    bot.reply_to(message, "🔴 Shutting down bot...")
    os._exit(1)

# --- ADMIN COMMAND: HELP ---
@bot.message_handler(commands=['help'])
def help_command(message):
    """Show help menu"""
    if is_admin(message.chat.id):
        # Show admin help
        admin_panel = (
            "╔══════════════════════╗\n"
            "║   🛡️ **ADMIN HELP**    ║\n"
            "╚══════════════════════╝\n\n"
            
            "**📁 FILE MANAGEMENT:**\n"
            "`/setfile` - Upload a new file\n"
            "`/files` - List all files\n"
            "`/delfile [key]` - Delete a file\n"
            "`/fileinfo [key]` - File details\n"
            "`/topfiles` - Most downloaded files\n"
            "`/searchfile [query]` - Search files\n\n"
            
            "**👑 ADMIN MANAGEMENT:**\n"
            "`/addadmin [user_id]` - Add new admin\n"
            "`/removeadmin [user_id]` - Remove admin\n"
            "`/admins` - List all admins\n"
            "`/setadminperm [user_id] [perm]` - Set permissions\n"
            "`/adminlog [user_id]` - View admin logs\n\n"
            
            "**🔗 VERIFICATION:**\n"
            "`/add [name] [@user]` - Add join button\n"
            "`/remove [@user]` - Remove button\n"
            "`/channels` - List channels\n"
            "`/setfixed [channel] [group]` - Set fixed\n"
            "`/checkmembership [id]` - Check user\n\n"
            
            "**📢 BROADCAST:**\n"
            "`/broadcast [msg]` - Send to all\n"
            "`/broadcastfwd` - Forward message\n"
            "`/schedule [time] [msg]` - Schedule\n"
            "`/cancelbroadcast [id]` - Cancel\n"
            "`/broadcaststatus` - Check status\n"
            "`/testbroadcast [msg]` - Test to admins\n\n"
            
            "**📊 STATISTICS:**\n"
            "`/stats` - Bot statistics\n"
            "`/userstats` - User activity stats\n"
            "`/filestats` - File statistics\n"
            "`/groupstats` - Group statistics\n"
            "`/commandstats` - Command usage stats\n"
            "`/hourlystats` - Hourly activity\n\n"
            
            "**🚫 BAN MANAGEMENT:**\n"
            "`/ban [id] [reason]` - Ban user\n"
            "`/unban [id]` - Unban user\n"
            "`/banned` - List banned\n"
            "`/warn [id] [reason]` - Warn user\n"
            "`/warnings [id]` - Check warnings\n"
            "`/resetwarns [id]` - Reset warnings\n\n"
            
            "**⚙️ SETTINGS:**\n"
            "`/settings` - View settings\n"
            "`/setwelcome [msg]` - Set welcome\n"
            "`/setgoodbye [msg]` - Set goodbye\n"
            "`/setrules [text]` - Set rules\n"
            "`/setlang [en/bn]` - Set language\n"
            "`/setbutton [name] [url]` - Custom button\n"
            "`/setantispam [on/off]` - Toggle anti-spam\n"
            "`/setlangfilter [on/off]` - Language filter\n"
            "`/setwordfilter [word]` - Add blocked word\n"
            "`/addfilter [word] [reply]` - Add auto-reply\n"
            "`/removefilter [word]` - Remove filter\n"
            "`/filters` - List all filters\n"
            "`/resetall` - Reset all settings\n\n"
            
            "**📝 USER MANAGEMENT:**\n"
            "`/userinfo [id]` - User details\n"
            "`/usernote [id] [note]` - Add note\n"
            "`/usernotes [id]` - View notes\n"
            "`/activity [id]` - User activity\n"
            "`/exportusers` - Export users\n"
            "`/importusers` - Import users\n\n"
            
            "**💬 GROUP MANAGEMENT:**\n"
            "`/groups` - List groups\n"
            "`/leave [id]` - Leave group\n"
            "`/setgrouptitle [title]` - Set title\n"
            "`/setgrouppic` - Set picture\n"
            "`/promote [id]` - Promote user\n"
            "`/demote [id]` - Demote user\n\n"
            
            "**🔐 SYSTEM:**\n"
            "`/backup` - Backup database\n"
            "`/restore` - Restore database\n"
            "`/listbackups` - List backups\n"
            "`/cleanup` - Clean old data\n"
            "`/optimize` - Optimize database\n"
            "`/resetstats` - Reset statistics\n"
            "`/log [lines]` - Get logs from group\n"
            "`/ping` - Check status\n"
            "`/uptime` - Bot uptime\n"
            "`/restart` - Restart bot\n"
            "`/shutdown` - Shutdown bot\n"
            "`/id` - Get user/chat ID\n"
            "`/info` - Bot information\n"
            "`/help` - Show this help"
        )
        bot.send_message(message.chat.id, admin_panel, parse_mode="Markdown")
    else:
        # Show user help
        user_help = (
            "👋 **Welcome to File Store Bot!**\n\n"
            "**What can I do?**\n"
            "• Store and share files\n"
            "• Require channel joins for access\n"
            "• Track downloads\n\n"
            "**How to use:**\n"
            "1. Click on any file link\n"
            "2. Join all required channels\n"
            "3. Click verify button\n"
            "4. Get your file instantly!\n\n"
            "**Commands:**\n"
            "`/start` - Start the bot\n"
            "`/help` - Show this help\n"
            "`/about` - About bot\n"
            "`/search [query]` - Search files\n"
            "`/stats` - Bot statistics\n"
            "`/report [issue]` - Report problem\n\n"
            "📌 **Need help?** Contact @mahfuj_offcial_143"
        )
        bot.send_message(message.chat.id, user_help, parse_mode="Markdown")

# --- ABOUT COMMAND ---
@bot.message_handler(commands=['about'])
def about(message):
    """About the bot"""
    about_text = (
        "**📁 File Store Bot**\n\n"
        "**Version:** 2.0\n"
        "**Developer:** @mahfuj_offcial_143\n"
        "**Language:** Python\n"
        "**Library:** PyTelegramBotAPI\n\n"
        "**Features:**\n"
        "✅ File storage with links\n"
        "✅ Channel verification\n"
        "✅ Multiple admins\n"
        "✅ Broadcast system\n"
        "✅ Download tracking\n"
        "✅ Auto-moderation\n"
        "✅ Backup & restore\n"
        "✅ Log group integration\n\n"
        "**Support:** @ANTIFOXSUPPORT"
    )
    bot.reply_to(message, about_text, parse_mode="Markdown")

# --- REPORT COMMAND ---
@bot.message_handler(commands=['report'])
def report_issue(message):
    """Report an issue to admins"""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/report Your issue here`", parse_mode="Markdown")
        return
    
    issue = parts[1]
    user_info = f"User: {message.from_user.id} (@{message.from_user.username or 'N/A'})"
    
    # Send to log group
    try:
        report_msg = f"""
**📝 NEW REPORT**

{user_info}

**Issue:** {issue}
"""
        bot.send_message(LOG_GROUP_ID, report_msg, parse_mode="Markdown")
        bot.reply_to(message, "✅ Report sent to admins. They will get back to you soon!")
    except:
        bot.reply_to(message, "❌ Failed to send report. Please try again later.")

# --- VERIFY & FILE DELIVERY ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("check_"))
def check_callback(call):
    """Handle verification callback"""
    file_key = call.data.replace("check_", "")
    user_id = call.from_user.id
    
    # Check if user is banned
    if is_user_banned(user_id):
        bot.answer_callback_query(call.id, "🚫 You are banned from using this bot.", show_alert=True)
        return
    
    try:
        extras = [row[0] for row in get_extra_list()]
        all_to_check = [FIXED_CH, FIXED_GR] + extras
        joined = True
        not_joined = []
        
        for username in all_to_check:
            try:
                status = bot.get_chat_member(f"@{username}", user_id).status
                if status not in ['member', 'administrator', 'creator']:
                    joined = False
                    not_joined.append(f"@{username}")
            except Exception as e:
                joined = False
                not_joined.append(f"@{username} (Error checking)")

        if joined:
            f = get_file_from_db(file_key)
            if f:
                f_id, f_type, f_cap, _ = f
                try:
                    if f_type == 'document':
                        bot.send_document(user_id, f_id, caption=f_cap)
                    elif f_type == 'video':
                        bot.send_video(user_id, f_id, caption=f_cap)
                    elif f_type == 'photo':
                        bot.send_photo(user_id, f_id, caption=f_cap)
                    elif f_type == 'text':
                        bot.send_message(user_id, f_cap)
                    
                    log_file_access(user_id, file_key, True)
                    bot.answer_callback_query(call.id, "✅ File sent successfully!")
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except Exception as e:
                    bot.answer_callback_query(call.id, "❌ Error sending file. Try again.", show_alert=True)
                    log_file_access(user_id, file_key, False)
                    log_error("File Send Error", str(e), user_id)
        else:
            not_joined_list = "\n".join(not_joined)
            bot.answer_callback_query(
                call.id, 
                f"❌ You haven't joined:\n{not_joined_list}", 
                show_alert=True
            )
            log_file_access(user_id, file_key, False)
    except Exception as e:
        bot.answer_callback_query(
            call.id, 
            "⚠️ Error: Make sure the bot is Admin in all channels.", 
            show_alert=True
        )
        log_error("Verification Error", str(e), user_id)

# --- RESET CONFIRMATION HANDLER ---
@bot.callback_query_handler(func=lambda call: call.data in ['confirm_reset', 'cancel_reset', 'confirm_reset_stats', 'cancel_reset_stats'])
def reset_confirmation(call):
    """Handle reset confirmations"""
    if call.data == 'confirm_reset':
        if not is_super_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Only super admins can reset.", show_alert=True)
            return
        
        # Delete all data
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        tables = ['files', 'extra_menu', 'stats', 'banned_users', 'admins', 'user_activity', 
                  'file_access_log', 'scheduled_broadcasts', 'filters', 'user_notes', 'command_stats', 'user_warnings']
        
        for table in tables:
            try:
                cursor.execute(f'DELETE FROM {table}')
            except:
                pass
        
        conn.commit()
        conn.close()
        
        # Clear chats file
        with open(CHATS_FILE, "w") as f:
            f.write("")
        
        all_chats.clear()
        
        log_to_group("FULL RESET", call.from_user.id, "All data has been reset")
        bot.edit_message_text(
            "✅ All data has been reset!",
            call.message.chat.id,
            call.message.message_id
        )
    
    elif call.data == 'cancel_reset':
        bot.edit_message_text(
            "❌ Reset cancelled.",
            call.message.chat.id,
            call.message.message_id
        )
    
    elif call.data == 'confirm_reset_stats':
        if not is_super_admin(call.from_user.id):
            bot.answer_callback_query(call.id, "❌ Only super admins can reset stats.", show_alert=True)
            return
        
        # Reset statistics
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM stats')
        cursor.execute('DELETE FROM command_stats')
        cursor.execute('DELETE FROM file_access_log')
        conn.commit()
        conn.close()
        
        log_to_group("STATS RESET", call.from_user.id, "Statistics have been reset")
        bot.edit_message_text(
            "✅ Statistics have been reset!",
            call.message.chat.id,
            call.message.message_id
        )
    
    elif call.data == 'cancel_reset_stats':
        bot.edit_message_text(
            "❌ Reset cancelled.",
            call.message.chat.id,
            call.message.message_id
        )

# --- FILE SETTING ---
@bot.message_handler(commands=['setfile'])
def set_file_init(message):
    """Start file upload process"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized to use this command.")
        return
    
    msg = bot.send_message(
        message.chat.id, 
        "📁 **Send the file** (Video/Document/Photo)\n\nOr just type some text to store.",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_content)

def process_content(message):
    """Process the uploaded content"""
    file_id = None
    f_type = None

    if message.document:
        file_id = message.document.file_id
        f_type = 'document'
        file_name = message.document.file_name
    elif message.video:
        file_id = message.video.file_id
        f_type = 'video'
        file_name = "video"
    elif message.photo:
        file_id = message.photo[-1].file_id
        f_type = 'photo'
        file_name = "photo"
    elif message.text:
        file_id = message.text
        f_type = 'text'
        file_name = "text"

    if file_id:
        if f_type != 'text':
            msg = bot.send_message(
                message.chat.id,
                f"📝 **Send caption for this file**\n\nFile: {file_name if 'file_name' in locals() else f_type}",
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, finalize_data, file_id, f_type)
        else:
            finalize_data(message, file_id, f_type)
    else:
        bot.send_message(message.chat.id, "❌ No file or text found. Try again with /setfile")

def finalize_data(message, file_id, f_type):
    """Finalize file upload and generate link"""
    caption = message.text if f_type != 'text' else file_id if f_type == 'text' else ""
    key = f"file_{int(time.time())}_{random.randint(1000, 9999)}"
    
    save_file_to_db(key, file_id, f_type, caption, message.chat.id)
    
    bot_user = bot.get_me().username
    file_link = f"https://t.me/{bot_user}?start={key}"
    
    # Create inline keyboard with link
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔗 Share Link", url=f"https://t.me/share/url?url={file_link}"))
    markup.add(types.InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_{key}"))
    
    bot.send_message(
        message.chat.id,
        f"✅ **File Stored Successfully!**\n\n"
        f"**Key:** `{key}`\n"
        f"**Type:** {f_type}\n"
        f"**Caption:** {caption[:50] if caption else 'No caption'}\n\n"
        f"**Shareable Link:**\n`{file_link}`",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# --- COPY LINK HANDLER ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("copy_"))
def copy_link(call):
    """Handle copy link button"""
    key = call.data.replace("copy_", "")
    bot_user = bot.get_me().username
    file_link = f"https://t.me/{bot_user}?start={key}"
    
    bot.answer_callback_query(call.id, f"Link: {file_link}", show_alert=True)

# --- FILES LIST COMMAND ---
@bot.message_handler(commands=['files'])
def list_files_cmd(message):
    """List all files (paginated)"""
    if not is_admin(message.chat.id):
        # Show public files for users
        files = get_all_files()[:10]
        if files:
            msg = "**📁 Available Files:**\n\n"
            for key, f_type, caption, downloads, _ in files:
                msg += f"• `{key}` - {caption[:30]}\n"
            msg += "\nUse /search to find more files."
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "No files available.")
        return
    
    # Admin view with pagination
    files = get_all_files()
    page = 1
    per_page = 10
    
    parts = message.text.split()
    if len(parts) > 1:
        try:
            page = int(parts[1])
        except:
            pass
    
    total_pages = (len(files) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    current_files = files[start:end]
    
    if current_files:
        msg = f"**📁 File List (Page {page}/{total_pages}):**\n\n"
        for key, f_type, caption, downloads, upload_date in current_files:
            date = datetime.datetime.fromtimestamp(upload_date).strftime("%Y-%m-%d")
            short_caption = (caption[:30] + "...") if len(caption) > 30 else caption
            msg += f"• `{key}`\n  Type: {f_type} | Downloads: {downloads} | Date: {date}\n  Caption: {short_caption}\n\n"
        
        # Navigation buttons
        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = []
        if page > 1:
            buttons.append(types.InlineKeyboardButton("◀️ Previous", callback_data=f"files_page_{page-1}"))
        if page < total_pages:
            buttons.append(types.InlineKeyboardButton("Next ▶️", callback_data=f"files_page_{page+1}"))
        markup.add(*buttons)
        
        bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "No files found.")

# --- FILES PAGE HANDLER ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("files_page_"))
def files_page(call):
    """Handle file list pagination"""
    page = int(call.data.replace("files_page_", ""))
    
    files = get_all_files()
    per_page = 10
    total_pages = (len(files) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    current_files = files[start:end]
    
    if current_files:
        msg = f"**📁 File List (Page {page}/{total_pages}):**\n\n"
        for key, f_type, caption, downloads, upload_date in current_files:
            date = datetime.datetime.fromtimestamp(upload_date).strftime("%Y-%m-%d")
            short_caption = (caption[:30] + "...") if len(caption) > 30 else caption
            msg += f"• `{key}`\n  Type: {f_type} | Downloads: {downloads} | Date: {date}\n  Caption: {short_caption}\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = []
        if page > 1:
            buttons.append(types.InlineKeyboardButton("◀️ Previous", callback_data=f"files_page_{page-1}"))
        if page < total_pages:
            buttons.append(types.InlineKeyboardButton("Next ▶️", callback_data=f"files_page_{page+1}"))
        markup.add(*buttons)
        
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "No files on this page.")

# --- DELETE FILE COMMAND ---
@bot.message_handler(commands=['delfile'])
def delete_file_cmd(message):
    """Delete a file"""
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not authorized.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/delfile file_key`", parse_mode="Markdown")
        return
    
    key = parts[1]
    file_data = get_file_from_db(key)
    
    if file_data:
        delete_file_from_db(key, message.chat.id)
        bot.reply_to(message, f"✅ File `{key}` has been deleted.", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"❌ File `{key}` not found.", parse_mode="Markdown")

# --- SEARCH COMMAND FOR USERS ---
@bot.message_handler(commands=['search'])
def search_files(message):
    """Search files (for users)"""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: `/search keyword`", parse_mode="Markdown")
        return
    
    query = parts[1].lower()
    files = get_all_files()
    
    results = []
    for key, f_type, caption, downloads, _ in files:
        if query in caption.lower():
            results.append((key, caption, downloads))
    
    if results:
        msg = f"**🔍 Search Results for '{query}':**\n\n"
        for key, caption, downloads in results[:10]:
            msg += f"• `{key}`\n  {caption[:50]}\n  Downloads: {downloads}\n\n"
        
        if len(results) > 10:
            msg += f"\n... and {len(results) - 10} more results."
        
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, f"❌ No files found matching '{query}'.")

# --- STATS COMMAND FOR USERS ---
@bot.message_handler(commands=['stats'])
def public_stats(message):
    """Show public statistics"""
    total_users = get_stat('total_users')
    total_files = len(get_all_files())
    total_downloads = get_stat('total_file_requests')
    
    msg = (
        "**📊 Bot Statistics**\n\n"
        f"👥 **Total Users:** {total_users}\n"
        f"📁 **Total Files:** {total_files}\n"
        f"⬇️ **Total Downloads:** {total_downloads}\n\n"
        "Made with ❤️ by @ANTIFOXSUPPORT"
    )
    
    bot.reply_to(message, msg, parse_mode="Markdown")

# --- MESSAGE HANDLER FOR FILTERS ---
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    """Handle all messages (for filters)"""
    # Check for filters
    if message.text and message.chat.type in ['group', 'supergroup']:
        # Check for exact match filters
        filter_data = get_filter(message.text.lower())
        if filter_data:
            response, response_type = filter_data
            bot.reply_to(message, response)
            return
        
        # Check for keyword in message
        filters = get_all_filters()
        for keyword, response, response_type in filters:
            if keyword in message.text.lower():
                bot.reply_to(message, response)
                return
        
        # Check for spam if enabled
        if get_setting('antispam') == 'on':
            # Simple spam detection (multiple messages in short time)
            # This would need a more sophisticated implementation
            pass
        
        # Check for language filter if enabled
        if get_setting('lang_filter') == 'on':
            # This would need language detection
            pass

# --- CHAT MEMBER HANDLERS ---
@bot.message_handler(content_types=['new_chat_members'])
def handle_new_members(message):
    """Handle new members joining group"""
    chat_id = message.chat.id
    welcome_msg = get_setting(f"welcome_{chat_id}")
    
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            # Bot was added to group
            bot.send_message(chat_id, "👋 Thanks for adding me! Use /help to see my commands.")
            add_group(chat_id, message.chat.title, message.chat.username, member.from_user.id if member.from_user else 0)
        elif welcome_msg:
            # New member joined
            welcome_text = welcome_msg.replace("{name}", member.first_name)
            bot.send_message(chat_id, welcome_text)

@bot.message_handler(content_types=['left_chat_member'])
def handle_left_member(message):
    """Handle members leaving group"""
    chat_id = message.chat.id
    goodbye_msg = get_setting(f"goodbye_{chat_id}")
    
    if message.left_chat_member.id == bot.get_me().id:
        # Bot was removed from group
        remove_group(chat_id, message.chat.title or "Unknown")
    elif goodbye_msg:
        # Member left
        goodbye_text = goodbye_msg.replace("{name}", message.left_chat_member.first_name)
        bot.send_message(chat_id, goodbye_text)

# --- SCHEDULED BROADCAST CHECKER ---
def check_scheduled_broadcasts():
    """Check and send scheduled broadcasts"""
    while True:
        try:
            pending = get_pending_broadcasts()
            for broadcast_id, message_text, scheduled_time in pending:
                success_count = 0
                failed_count = 0
                
                for chat_id in list(all_chats):
                    try:
                        bot.send_message(chat_id, message_text)
                        success_count += 1
                        time.sleep(0.05)
                    except:
                        failed_count += 1
                
                update_broadcast_status(broadcast_id, 'completed')
                
                # Notify creator
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute('SELECT created_by FROM scheduled_broadcasts WHERE id=?', (broadcast_id,))
                created_by = cursor.fetchone()[0]
                conn.close()
                
                try:
                    bot.send_message(
                        created_by,
                        f"✅ **Scheduled Broadcast Completed!**\n\n"
                        f"📨 Sent to: {success_count}\n"
                        f"❌ Failed: {failed_count}",
                        parse_mode="Markdown"
                    )
                except:
                    pass
                
                # Log to group
                log_broadcast(created_by, success_count, failed_count, message_text[:100])
            
            time.sleep(60)  # Check every minute
        except Exception as e:
            log_error("Scheduled Broadcast Error", str(e))
            time.sleep(60)

# Start scheduled broadcast checker in a separate thread
threading.Thread(target=check_scheduled_broadcasts, daemon=True).start()

# --- FLASK KEEP ALIVE SERVER FOR RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "I'am MAFU FILE STORE BOT"

def run_flask():
    # Make sure to run on port provided by environment or default to 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True  # Allows program to exit even if this thread is running
    t.start()
    print("Flask Keep-Alive server started for Render.")

# --- MAIN ---
if __name__ == "__main__":
    print("🤖 Bot is starting...")
    print(f"👤 Bot Username: @{bot.get_me().username}")
    print(f"👑 Super Admins: {SUPER_ADMIN_IDS}")
    print(f"👥 Regular Admins: {ADMIN_IDS}")
    print(f"📋 Log Group ID: {LOG_GROUP_ID}")
    
    # Start Flask keep-alive server for Render
    keep_alive()
    
    print("✅ Bot is running!")
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"❌ Error: {e}")
        log_error("Bot Crash", str(e))
        time.sleep(5)
        os._exit(0)
