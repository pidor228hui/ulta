import aiosqlite
import os
from datetime import datetime
from typing import Optional

from cryptography.fernet import Fernet

DB_FOLDER = "dbs"
os.makedirs(DB_FOLDER, exist_ok=True)
AUTH_DB_PATH = os.path.join(DB_FOLDER, "auth.db")

def get_db_path(token):
    token_short = token[:8]  # первые 8 символов токена
    return os.path.join(DB_FOLDER, f"db_{token_short}.db")

async def is_user_connected(token: str, user_id: int) -> bool:
    token_from_db = await get_vk_token(user_id)
    return token_from_db is not None

def _get_fernet() -> Fernet:
    key = os.getenv("AUTH_ENCRYPTION_KEY")
    if not key:
        raise ValueError("AUTH_ENCRYPTION_KEY is not set")
    return Fernet(key)

async def _ensure_auth_table(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS vk_auth (
            vk_user_id INTEGER PRIMARY KEY,
            telegram_user_id INTEGER NOT NULL,
            token_encrypted BLOB NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

async def store_vk_token(vk_user_id: int, telegram_user_id: int, token: str) -> None:
    fernet = _get_fernet()
    encrypted_token = fernet.encrypt(token.encode("utf-8"))
    async with aiosqlite.connect(AUTH_DB_PATH) as db:
        await _ensure_auth_table(db)
        await db.execute(
            """
            INSERT OR REPLACE INTO vk_auth (
                vk_user_id,
                telegram_user_id,
                token_encrypted,
                created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (vk_user_id, telegram_user_id, encrypted_token, datetime.utcnow().isoformat()),
        )
        await db.commit()

async def get_vk_token(vk_user_id: int) -> Optional[str]:
    fernet = _get_fernet()
    async with aiosqlite.connect(AUTH_DB_PATH) as db:
        await _ensure_auth_table(db)
        cursor = await db.execute(
            "SELECT token_encrypted FROM vk_auth WHERE vk_user_id = ?",
            (vk_user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return fernet.decrypt(row[0]).decode("utf-8")

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
