import aiosqlite
import datetime
import config
import secrets

DB_PATH = config.DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as conn:
        # --- Tables for Nafuzor ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                balance REAL DEFAULT 0.0,
                subscription TEXT DEFAULT 'None',
                referrer_id INTEGER,
                card_number TEXT,
                card_cvv TEXT,
                card_balance REAL DEFAULT 0.0,
                card_active INTEGER DEFAULT 0,
                card_blocked INTEGER DEFAULT 0,
                api_token TEXT,
                has_trigger INTEGER DEFAULT 0
            )
        """)
        
        # Миграция для старых баз (если колонка уже есть - ошибка игнорируется)
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN has_trigger INTEGER DEFAULT 0")
        except: pass

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                number TEXT,
                category TEXT,
                status TEXT DEFAULT 'waiting', 
                added_at TEXT,
                code_entered_at TEXT,
                hold_minutes INTEGER DEFAULT 0,
                payout REAL DEFAULT 0.0,
                is_trigger INTEGER DEFAULT 0
            )
        """)
        
        # --- TRIGGER TABLES ---
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trigger_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trigger_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_id INTEGER,
                user_id INTEGER,
                number TEXT,
                category TEXT,
                run_time TEXT
            )
        """)

        # Settings & Logs
        await conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        await conn.execute("CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, method TEXT, date TEXT)")
        await conn.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, action TEXT, details TEXT, date TEXT)")
        await conn.execute("CREATE TABLE IF NOT EXISTS card_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, amount REAL, from_user TEXT, date TEXT)")
        
        # --- Tables for Lixcuk ---
        await conn.execute("CREATE TABLE IF NOT EXISTS lixcuk_sessions (lixcuk_id INTEGER PRIMARY KEY, nafuzor_user_id INTEGER)")
        await conn.execute("CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, lixcuk_id INTEGER, amount REAL, status TEXT, date TEXT, admin_name TEXT, target_username TEXT)")
        await conn.execute("CREATE TABLE IF NOT EXISTS lixcuk_users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, joined_at TEXT)")
        await conn.execute("CREATE TABLE IF NOT EXISTS lixcuk_admins (user_id INTEGER PRIMARY KEY, username TEXT)")
        await conn.execute("CREATE TABLE IF NOT EXISTS lixcuk_settings (key TEXT PRIMARY KEY, value TEXT)")

        # Defaults
        await conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('check_sub', '1')")
        await conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('check_username', '0')")
        await conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('nag_card', '1')")
        await conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('work_status', 'Full work🟢')")
        await conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('disabled_sections', '')")
        
        await conn.execute("INSERT OR IGNORE INTO lixcuk_settings (key, value) VALUES ('notify_withdraw', '1')")
        await conn.execute("INSERT OR IGNORE INTO lixcuk_settings (key, value) VALUES ('disabled_sections', '')")
        await conn.execute("INSERT OR IGNORE INTO lixcuk_admins (user_id, username) VALUES (?, ?)", (config.ADMIN_ID, "MainAdmin"))

        await conn.commit()

# --- BASIC METHODS ---

async def add_user(user_id, username, full_name, referrer_id=None):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, referrer_id) VALUES (?, ?, ?, ?)", 
                           (user_id, username, full_name, referrer_id))
        await conn.execute("UPDATE users SET username=?, full_name=? WHERE user_id=?", (username, full_name, user_id))
        
        # Генерация карты
        import random
        card = "4" + "".join([str(random.randint(0, 9)) for _ in range(15)])
        cvv = "".join([str(random.randint(0, 9)) for _ in range(3)])
        await conn.execute("UPDATE users SET card_number=?, card_cvv=? WHERE user_id=? AND card_number IS NULL", (card, cvv, user_id))
        await conn.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def get_user_by_username(username):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        username = username.replace("@", "")
        async with conn.execute("SELECT * FROM users WHERE username LIKE ?", (f"{username}",)) as cursor:
            return await cursor.fetchone()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM users") as cursor:
            return await cursor.fetchall()

# --- SETTINGS & INFO ---

async def get_settings(key):
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT value FROM settings WHERE key=?", (key,)) as cursor:
            res = await cursor.fetchone()
            return res[0] if res else ""

async def set_settings(key, value):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await conn.commit()

async def get_queue_count():
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT count(*) FROM numbers WHERE status='waiting'") as cursor:
            return (await cursor.fetchone())[0]

# --- TRIGGER METHODS ---

async def buy_trigger(user_id, cost):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE users SET balance = balance - ?, has_trigger = 1 WHERE user_id = ?", (cost, user_id))
        await conn.commit()

async def create_trigger_config(user_id, name):
    async with aiosqlite.connect(DB_PATH) as conn:
        cursor = await conn.execute("INSERT INTO trigger_configs (user_id, name) VALUES (?, ?)", (user_id, name))
        await conn.commit()
        return cursor.lastrowid # Возвращаем ID созданного конфига

async def get_trigger_configs(user_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT id, name FROM trigger_configs WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchall()

async def get_config_name(config_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT name FROM trigger_configs WHERE id=?", (config_id,)) as cur:
            res = await cur.fetchone()
            return res[0] if res else "Unknown"

async def add_trigger_task(config_id, user_id, number, category, run_time):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("INSERT INTO trigger_tasks (config_id, user_id, number, category, run_time) VALUES (?, ?, ?, ?, ?)",
                           (config_id, user_id, number, category, run_time))
        await conn.commit()

async def get_tasks_in_config(config_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT id, number, category, run_time FROM trigger_tasks WHERE config_id=?", (config_id,)) as cur:
            return await cur.fetchall()

async def get_task(task_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM trigger_tasks WHERE id=?", (task_id,)) as cur:
            return await cur.fetchone()

async def update_task_number(task_id, number, category):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE trigger_tasks SET number=?, category=? WHERE id=?", (number, category, task_id))
        await conn.commit()

async def update_task_time(task_id, run_time):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE trigger_tasks SET run_time=? WHERE id=?", (run_time, task_id))
        await conn.commit()

async def get_ready_tasks():
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM trigger_tasks WHERE run_time <= ?", (now_str,)) as cur:
            return await cur.fetchall()

async def execute_task(task_id):
    task = await get_task(task_id)
    if not task: return
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("INSERT INTO numbers (user_id, number, category, added_at, is_trigger) VALUES (?, ?, ?, ?, 1)",
                           (task['user_id'], task['number'], task['category'], datetime.datetime.now()))
        await conn.execute("DELETE FROM trigger_tasks WHERE id=?", (task_id,))
        await conn.commit()

# --- CARD & FINANCE ---

async def activate_card(user_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE users SET card_active=1 WHERE user_id=?", (user_id,))
        await conn.commit()

async def add_card_transaction(user_id, type_op, amount, from_user):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("INSERT INTO card_history (user_id, type, amount, from_user, date) VALUES (?, ?, ?, ?, ?)", 
                           (user_id, type_op, amount, from_user, datetime.datetime.now()))
        await conn.commit()

async def get_card_history(user_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT type, amount, from_user, date FROM card_history WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,)) as cur: 
            return await cur.fetchall()

async def add_log(user_id, username, action, details):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("INSERT INTO logs (user_id, username, action, details, date) VALUES (?, ?, ?, ?, ?)", 
                           (user_id, username, action, details, datetime.datetime.now()))
        await conn.commit()

async def get_logs_by_username(username):
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT date, action, details FROM logs WHERE username=? ORDER BY id DESC LIMIT 50", (username,)) as cur: 
            return await cur.fetchall()

async def add_payment(user_id, amount, method):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("INSERT INTO payments (user_id, amount, method, date) VALUES (?, ?, ?, ?)", 
                           (user_id, amount, method, datetime.datetime.now()))
        await conn.commit()

async def get_payment_history(user_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT amount, method, date FROM payments WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,)) as cur: 
            return await cur.fetchall()

# --- API & TOKENS ---

async def generate_api_token(user_id):
    random_part = secrets.token_urlsafe(16)
    token = f"{user_id}-{random_part}"
    async with aiosqlite.connect(DB_PATH) as conn: 
        await conn.execute("UPDATE users SET api_token = ? WHERE user_id = ?", (token, user_id))
        await conn.commit()
    return token

async def reset_api_token(user_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE users SET api_token = NULL WHERE user_id = ?", (user_id,))
        
        # Исправленный блок
        sql_find = "SELECT lixcuk_id FROM lixcuk_sessions WHERE nafuzor_user_id=?"
        async with conn.execute(sql_find, (user_id,)) as cur: 
            rows = await cur.fetchall()
            for r in rows: 
                await conn.execute("DELETE FROM lixcuk_sessions WHERE lixcuk_id=?", (r[0],))
        await conn.commit()

async def is_admin(user_id): 
    return user_id == config.ADMIN_ID

async def set_admin(user_id, status): 
    pass

# --- LIXCUK METHODS ---

async def add_lixcuk_user(user_id, username, full_name):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("INSERT OR IGNORE INTO lixcuk_users (user_id, username, full_name, joined_at) VALUES (?, ?, ?, ?)",
                           (user_id, username, full_name, datetime.datetime.now()))
        await conn.execute("UPDATE lixcuk_users SET username=?, full_name=? WHERE user_id=?", (username, full_name, user_id))
        await conn.commit()

async def get_all_lixcuk_users():
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM lixcuk_users") as cur:
            return await cur.fetchall()

async def connect_lixcuk_card(lixcuk_id, card_number, cv, token):
    async with aiosqlite.connect(DB_PATH) as conn:
        sql = "SELECT user_id, api_token FROM users WHERE card_number=? AND card_cvv=?"
        async with conn.execute(sql, (card_number, cv)) as cur:
            res = await cur.fetchone()
            
        if res and res[1] == token:
            await conn.execute("INSERT OR REPLACE INTO lixcuk_sessions (lixcuk_id, nafuzor_user_id) VALUES (?, ?)", (lixcuk_id, res[0]))
            await conn.commit()
            return True
        return False

async def get_lixcuk_session(lixcuk_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        sql = """
            SELECT u.user_id, u.username, u.card_balance, u.card_number, u.card_cvv 
            FROM lixcuk_sessions ls 
            JOIN users u ON ls.nafuzor_user_id = u.user_id 
            WHERE ls.lixcuk_id = ?
        """
        async with conn.execute(sql, (lixcuk_id,)) as cur:
            return await cur.fetchone()

async def disconnect_lixcuk_card(lixcuk_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("DELETE FROM lixcuk_sessions WHERE lixcuk_id=?", (lixcuk_id,))
        await conn.commit()

async def create_withdrawal(lixcuk_id, nafuzor_uid, amount, target_username):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE users SET card_balance = card_balance - ? WHERE user_id=?", (amount, nafuzor_uid))
        await conn.execute("INSERT INTO withdrawals (user_id, lixcuk_id, amount, status, date, target_username) VALUES (?, ?, ?, ?, ?, ?)", 
                           (nafuzor_uid, lixcuk_id, amount, 'waiting', datetime.datetime.now(), target_username))
        await conn.commit()

async def get_withdrawals(status, limit=None):
    sql = "SELECT w.id, w.amount, w.target_username, w.date FROM withdrawals w"
    params = []
    if status:
        sql += " WHERE w.status = ?"
        params.append(status)
    else:
        sql += " ORDER BY w.date DESC"
        
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
        
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute(sql, tuple(params)) as cur:
            return await cur.fetchall()

async def get_user_withdrawals(lixcuk_id, status):
    async with aiosqlite.connect(DB_PATH) as conn:
        sql = "SELECT id, amount, date, status FROM withdrawals WHERE lixcuk_id=? AND status=?"
        async with conn.execute(sql, (lixcuk_id, status)) as cur:
            return await cur.fetchall()

async def update_withdrawal_status(wid, status, admin_name="System"):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE withdrawals SET status=?, admin_name=? WHERE id=?", (status, admin_name, wid))
        await conn.commit()
        async with conn.execute("SELECT lixcuk_id FROM withdrawals WHERE id=?", (wid,)) as cur:
            res = await cur.fetchone()
            return res[0] if res else None

async def get_withdraw_details(wid):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        sql = "SELECT w.id, w.amount, w.target_username, w.date, w.status, u.card_number FROM withdrawals w JOIN users u ON w.user_id = u.user_id WHERE w.id=?"
        async with conn.execute(sql, (wid,)) as cur:
            return await cur.fetchone()

async def get_all_withdrawals_report():
    async with aiosqlite.connect(DB_PATH) as conn:
        sql = "SELECT w.id, w.target_username, w.amount, w.status, w.date, w.admin_name FROM withdrawals w WHERE w.date >= date('now', 'start of day')"
        async with conn.execute(sql) as cur:
            return await cur.fetchall()

async def is_lixcuk_admin(user_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT 1 FROM lixcuk_admins WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone() is not None

async def add_lixcuk_admin(user_id, username):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("INSERT OR REPLACE INTO lixcuk_admins (user_id, username) VALUES (?, ?)", (user_id, username))
        await conn.commit()

async def remove_lixcuk_admin(username):
    username = username.replace("@", "")
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("DELETE FROM lixcuk_admins WHERE username=?", (username,))
        await conn.commit()

async def get_lixcuk_admins():
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT user_id FROM lixcuk_admins") as cur:
            return await cur.fetchall()

async def get_lixcuk_setting(key):
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT value FROM lixcuk_settings WHERE key=?", (key,)) as cursor:
            res = await cursor.fetchone()
            return res[0] if res else ""

async def set_lixcuk_setting(key, value):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("INSERT OR REPLACE INTO lixcuk_settings (key, value) VALUES (?, ?)", (key, value))
        await conn.commit()