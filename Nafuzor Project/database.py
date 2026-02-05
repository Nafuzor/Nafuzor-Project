import sqlite3
from config import ADMIN_ID

DB_NAME = "bot_database.db"

def create_tables():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Пользователи
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance_rub REAL DEFAULT 0,
        subscription TEXT DEFAULT 'none',
        sub_expiry TEXT,
        referrer_id INTEGER,
        reputation INTEGER DEFAULT 0,
        ref_earnings REAL DEFAULT 0
    )''')
    
    # Номера
    c.execute('''CREATE TABLE IF NOT EXISTS numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        number TEXT,
        category TEXT,
        status TEXT DEFAULT 'Ожидает',
        created_at TEXT,
        entered_at TEXT,
        drop_time TEXT,
        hold_time TEXT,
        payout_amount REAL DEFAULT 0
    )''')
    
    # Карты
    c.execute('''CREATE TABLE IF NOT EXISTS cards (
        user_id INTEGER PRIMARY KEY,
        card_number TEXT,
        cvv TEXT,
        balance REAL DEFAULT 0,
        is_active INTEGER DEFAULT 0,
        is_blocked INTEGER DEFAULT 0,
        created_at TEXT
    )''')

    # Платежи
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
        order_id TEXT PRIMARY KEY,
        user_id INTEGER,
        amount_rub REAL,
        system TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )''')
    
    # Админы
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY
    )''')
    
    # Настройки
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # Дефолтные настройки
    defaults = {
        'work_status': '🟢 Активен',
        'queue_count': '0',
        'check_sub': '1',
        'check_username': '1',
        'check_card': '1',
        'latest_news': ''
    }
    for key, val in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))
        
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (ADMIN_ID,))

    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_NAME)

# --- Helpers ---

def add_user(user_id, username, referrer_id=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)", 
              (user_id, username, referrer_id))
    if username:
        c.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    data = c.fetchone()
    conn.close()
    return data

def is_admin(user_id):
    if user_id == ADMIN_ID: return True
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    conn.close()
    return bool(res)

def get_setting(key):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else ""

def get_setting_bool(key):
    val = get_setting(key)
    return val == '1'

def set_setting(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def is_section_disabled(section_key):
    val = get_setting(f"dis_{section_key}")
    return val == '1'

# --- Payments ---

def create_payment(order_id, user_id, amount, system):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO payments (order_id, user_id, amount_rub, system, created_at) VALUES (?, ?, ?, ?, datetime('now'))", 
              (str(order_id), user_id, amount, system))
    conn.commit()
    conn.close()

def get_payment(order_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM payments WHERE order_id = ?", (str(order_id),))
    res = c.fetchone()
    conn.close()
    return res

def set_payment_paid(order_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE payments SET status = 'paid' WHERE order_id = ?", (str(order_id),))
    conn.commit()
    conn.close()

def get_user_payments(user_id, limit=10):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT system, amount_rub, created_at, order_id FROM payments WHERE user_id = ? AND status = 'paid' ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows