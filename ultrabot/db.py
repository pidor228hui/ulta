import aiosqlite
import os

DB_FOLDER = "dbs"
os.makedirs(DB_FOLDER, exist_ok=True)

def get_db_path(token):
    token_short = token[:8]  # первые 8 символов токена
    return os.path.join(DB_FOLDER, f"db_{token_short}.db")

async def is_user_connected(token: str, user_id: int) -> bool:
    db_path = f"data/{token}.db"

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT 1 FROM messages WHERE user_id = ? LIMIT 1",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row is not None

# ------------------------
# Работа с префиксами
# ------------------------
async def get_prefixes(token):
    db_path = get_db_path(token)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS prefixes (prefix TEXT PRIMARY KEY)")
        cursor = await db.execute("SELECT prefix FROM prefixes")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]

async def add_prefix(token, prefix):
    db_path = get_db_path(token)
    async with aiosqlite.connect(db_path) as db:
        try:
            await db.execute("INSERT INTO prefixes (prefix) VALUES (?)", (prefix,))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def remove_prefix(token, prefix):
    db_path = get_db_path(token)
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("DELETE FROM prefixes WHERE prefix=?", (prefix,))
        await db.commit()
        return cursor.rowcount > 0

# ------------------------
# Работа с сообщениями
# ------------------------
async def increment_message_count(token, user_id):
    db_path = get_db_path(token)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS messages (user_id INTEGER PRIMARY KEY, count INTEGER DEFAULT 0)")
        cursor = await db.execute("SELECT count FROM messages WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        if row:
            await db.execute("UPDATE messages SET count=count+1 WHERE user_id=?", (user_id,))
        else:
            await db.execute("INSERT INTO messages (user_id, count) VALUES (?, 1)", (user_id,))
        await db.commit()

async def get_message_count(token, user_id):
    db_path = get_db_path(token)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS messages (user_id INTEGER PRIMARY KEY, count INTEGER DEFAULT 0)")
        cursor = await db.execute("SELECT count FROM messages WHERE user_id=?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0

# ------------------------
# Работа с последними сообщениями
# ------------------------
async def get_last_message_id(token, peer_id):
    db_path = get_db_path(token)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS last_messages (peer_id INTEGER PRIMARY KEY, msg_id INTEGER)")
        cursor = await db.execute("SELECT msg_id FROM last_messages WHERE peer_id=?", (peer_id,))
        row = await cursor.fetchone()
        return row[0] if row else None

async def set_last_message_id(token, peer_id, msg_id):
    db_path = get_db_path(token)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS last_messages (peer_id INTEGER PRIMARY KEY, msg_id INTEGER)")
        await db.execute("INSERT OR REPLACE INTO last_messages (peer_id, msg_id) VALUES (?, ?)", (peer_id, msg_id))
        await db.commit()
