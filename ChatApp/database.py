import aiosqlite
from contextlib import asynccontextmanager
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import os
import aiofiles

from ChatApp.config import DATABASE_URL, UPLOAD_DIR
from ChatApp.pydantic_models import SessionInfo, MessageResponse

logger = logging.getLogger(__name__)


async def init_db():
    """初始化数据库表"""
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        # 迁移：为已有数据库添加 title 列
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN title TEXT")
        except Exception:
            pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                idx INTEGER NOT NULL,
                role TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                message_id INTEGER,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
                FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE
            )
        """)
        await db.commit()
        logger.info("Database initialized")


async def get_db():
    """数据库连接依赖"""
    conn = await aiosqlite.connect(DATABASE_URL)
    await conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        await conn.close()


# ---------- 用户相关数据库操作 ----------
async def get_user_by_username(db: aiosqlite.Connection, username: str):
    cursor = await db.execute("SELECT id, username, hashed_password FROM users WHERE username = ?", (username,))
    row = await cursor.fetchone()
    if row:
        return {"id": row[0], "username": row[1], "hashed_password": row[2]}
    return None


async def create_user(db: aiosqlite.Connection, username: str, hashed_password: str):
    try:
        cursor = await db.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", (username, hashed_password))
        await db.commit()
        logger.info(f"User registered: {username}")
        return cursor.lastrowid
    except aiosqlite.IntegrityError:
        logger.warning(f"Registration failed: username '{username}' already exists")
        return None


# ---------- 会话相关数据库操作 ----------
async def create_session_db(db: aiosqlite.Connection, user_id: int) -> str:
    session_id = str(uuid.uuid4())
    await db.execute("INSERT INTO sessions (id, user_id) VALUES (?, ?)", (session_id, user_id))
    await db.commit()
    logger.info(f"Session created: {session_id} for user_id={user_id}")
    return session_id


async def get_sessions_db(db: aiosqlite.Connection, user_id: int) -> List[SessionInfo]:
    cursor = await db.execute(
        "SELECT id, title, created_at FROM sessions WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = await cursor.fetchall()
    return [SessionInfo(session_id=row[0], title=row[1], created_at=datetime.fromisoformat(row[2])) for row in rows]


async def update_session_title_db(db: aiosqlite.Connection, session_id: str, title: str):
    await db.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
    await db.commit()
    logger.info(f"Session {session_id} title updated: {title}")


async def get_session_title_db(db: aiosqlite.Connection, session_id: str) -> str | None:
    cursor = await db.execute("SELECT title FROM sessions WHERE id = ?", (session_id,))
    row = await cursor.fetchone()
    return row[0] if row else None


async def session_belongs_to_user(db: aiosqlite.Connection, session_id: str, user_id: int) -> bool:
    cursor = await db.execute("SELECT 1 FROM sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
    row = await cursor.fetchone()
    return row is not None


# ---------- 消息相关数据库操作 ----------
async def get_messages_db(db: aiosqlite.Connection, session_id: str, user_id: int) -> List[MessageResponse]:
    # 验证会话属于该用户
    if not await session_belongs_to_user(db, session_id, user_id):
        raise Exception("Session not exists or Unauthenticated")
    cursor = await db.execute(
        "SELECT id, idx, role, type, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at",
        (session_id,)
    )
    rows = await cursor.fetchall()
    return [
        MessageResponse(
            id=row[0],
            idx=row[1],
            role=row[2],
            type=row[3],
            content=row[4],
            created_at=datetime.fromisoformat(row[5]),
        )
        for row in rows
    ]

async def get_message_db(db: aiosqlite.Connection, message_id: int) -> MessageResponse:
    cursor = await db.execute(
        "SELECT id, idx, role, type, content, created_at FROM messages WHERE id = ?",
        (message_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise Exception("Message not exists")
    return MessageResponse(
        id=row[0],
        idx=row[1],
        role=row[2],
        type=row[3],
        content=row[4],
        created_at=datetime.fromisoformat(row[5]),
    )

async def save_message_db(db: aiosqlite.Connection, session_id: str, idx: int, role: str, type_: str,
                          content: str) -> int:
    cursor = await db.execute(
        "INSERT INTO messages (session_id, idx, role, type, content) VALUES (?, ?, ?, ?, ?)",
        (session_id, idx, role, type_, content)
    )
    await db.commit()
    return cursor.lastrowid

async def update_message_db(db: aiosqlite.Connection, message_id: int, content: str):
    await db.execute("UPDATE messages SET content = ? WHERE id = ?",(content, message_id))
    await db.commit()

# ---------- 文件相关数据库操作 ----------
async def save_file_record_db(
        db: aiosqlite.Connection,
        file_id: str,
        session_id: str,
        message_id: Optional[int],
        original_filename: str,
        stored_filename: str,
        file_path: str,
        file_size: int,
        mime_type: str
) -> None:
    await db.execute(
        """INSERT INTO files (id, session_id, message_id, original_filename, stored_filename, file_path, file_size, mime_type)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (file_id, session_id, message_id, original_filename, stored_filename, file_path, file_size, mime_type)
    )
    await db.commit()
    logger.info(f"File record saved: {file_id} for session {session_id}")


async def get_file_record_db(db: aiosqlite.Connection, file_id: str):
    cursor = await db.execute(
        "SELECT id, original_filename, stored_filename, file_path, file_size, mime_type FROM files WHERE id = ?",
        (file_id,)
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "original_filename": row[1],
        "stored_filename": row[2],
        "file_path": row[3],
        "file_size": row[4],
        "mime_type": row[5]
    }


async def get_message_attachments_db(db: aiosqlite.Connection, session_id: str, message_id: Optional[int]):
    if message_id is not None:
        cursor = await db.execute(
            "SELECT id, original_filename, stored_filename, file_path, file_size, mime_type FROM files WHERE session_id = ? AND message_id = ?",
            (session_id, message_id,)
        )
    else:
        cursor = await db.execute(
            "SELECT id, original_filename, stored_filename, file_path, file_size, mime_type FROM files WHERE session_id = ? AND message_id IS NULL",
            (session_id,)
        )
    rows = await cursor.fetchall()
    if not rows:
        return None
    return [{
        "id": row[0],
        "original_filename": row[1],
        "stored_filename": row[2],
        "file_path": row[3],
        "file_size": row[4],
        "mime_type": row[5]
    } for row in rows]


async def save_file(
        session_id: str,
        message_id: Optional[int],
        file_bytes: bytes,
        original_filename: str,
        mime_type: str,
        db: aiosqlite.Connection
) -> dict:
    """将字节数据保存为文件，并记录到数据库 files 表中。"""
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(original_filename)[1] or ""
    stored_filename = f"{file_id}{ext}"

    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    file_path = os.path.join(session_dir, stored_filename)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_bytes)
    file_size = len(file_bytes)

    await save_file_record_db(
        db=db,
        file_id=file_id,
        session_id=session_id,
        message_id=message_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type
    )

    logger.info(f"File saved: {file_path} (size={file_size})")
    return {
        "file_id": file_id,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "file_path": file_path,
        "size": file_size,
        "mime_type": mime_type
    }