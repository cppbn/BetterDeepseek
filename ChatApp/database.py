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
        try:
            await db.execute("ALTER TABLE sessions ADD COLUMN title TEXT")
        except Exception:
            pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                idx INTEGER NOT NULL,
                role TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)
        try:
            await db.execute("ALTER TABLE messages ADD COLUMN seq INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
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
        await _init_model_configs(db)
        await _init_token_usage(db)
        logger.info("Database initialized")


async def _init_model_configs(db: aiosqlite.Connection):
    """Create model_configs table and seed defaults if empty."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS model_configs (
            key TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            thinking INTEGER DEFAULT 0,
            accept_image INTEGER DEFAULT 0,
            accept_audio INTEGER DEFAULT 0,
            is_default INTEGER DEFAULT 0,
            category TEXT NOT NULL DEFAULT 'chat'
        )
    """)
    cursor = await db.execute("SELECT COUNT(*) FROM model_configs")
    count = (await cursor.fetchone())[0]
    if count == 0:
        defaults = [
            ("default", "deepseek", "deepseek-reasoner", 1, 0, 0, 1, "chat"),
            ("deepseek-v4-flash-thinking", "deepseek", "deepseek-v4-flash", 1, 0, 0, 0, "chat"),
            ("deepseek-v4-pro-thinking", "deepseek", "deepseek-v4-pro", 1, 0, 0, 0, "chat"),
            ("qwen3.6-plus-thinking", "openrouter", "qwen/qwen3.6-plus", 1, 1, 0, 0, "chat"),
            ("qwen3.5-flash-thinking", "openrouter", "qwen/qwen3.5-flash-02-23", 1, 1, 0, 0, "chat"),
            ("kimi-k2.6-thinking", "openrouter", "moonshotai/kimi-k2.6", 1, 1, 0, 0, "chat"),
            ("glm-5.1-thinking", "openrouter", "z-ai/glm-5.1", 1, 0, 0, 0, "chat"),
            ("mino-v2.5-thinking", "openrouter", "xiaomi/mimo-v2.5", 1, 1, 1, 0, "chat"),
            ("image_transcription", "openrouter", "qwen/qwen3.5-flash-02-23", 0, 0, 0, 0, "image"),
            ("audio_transcription", "openrouter", "xiaomi/mimo-v2.5", 0, 0, 0, 0, "audio"),
            ("title_generation", "deepseek", "deepseek-chat", 0, 0, 0, 0, "title"),
        ]
        await db.executemany(
            "INSERT INTO model_configs (key, provider, model, thinking, accept_image, accept_audio, is_default, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            defaults
        )
        await db.commit()
        logger.info("Seeded default model configurations")


async def _init_token_usage(db: aiosqlite.Connection):
    """Create token_usage table."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            model TEXT NOT NULL,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)
    await db.commit()


async def get_db():
    """数据库连接依赖"""
    conn = await aiosqlite.connect(DATABASE_URL)
    await conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        await conn.close()


# ---------- 模型配置相关 ----------
async def get_all_model_configs_db(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute("SELECT key, provider, model, thinking, accept_image, accept_audio, is_default, category FROM model_configs")
    rows = await cursor.fetchall()
    return [{"key": r[0], "provider": r[1], "model": r[2], "thinking": bool(r[3]),
             "accept_image": bool(r[4]), "accept_audio": bool(r[5]), "is_default": bool(r[6]), "category": r[7]} for r in rows]


async def get_model_config_db(db: aiosqlite.Connection, key: str) -> dict | None:
    cursor = await db.execute("SELECT key, provider, model, thinking, accept_image, accept_audio, is_default, category FROM model_configs WHERE key = ?", (key,))
    row = await cursor.fetchone()
    if not row:
        return None
    return {"key": row[0], "provider": row[1], "model": row[2], "thinking": bool(row[3]),
            "accept_image": bool(row[4]), "accept_audio": bool(row[5]), "is_default": bool(row[6]), "category": row[7]}


async def upsert_model_config_db(db: aiosqlite.Connection, key: str, provider: str, model: str,
                                  thinking: int, accept_image: int, accept_audio: int,
                                  is_default: int, category: str):
    if is_default:
        await db.execute("UPDATE model_configs SET is_default = 0 WHERE category = ?", (category,))
    await db.execute(
        "INSERT OR REPLACE INTO model_configs (key, provider, model, thinking, accept_image, accept_audio, is_default, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (key, provider, model, thinking, accept_image, accept_audio, is_default, category)
    )
    await db.commit()


async def delete_model_config_db(db: aiosqlite.Connection, key: str) -> bool:
    cursor = await db.execute("DELETE FROM model_configs WHERE key = ?", (key,))
    await db.commit()
    return cursor.rowcount > 0


async def get_model_config_by_category_db(db: aiosqlite.Connection, category: str) -> dict | None:
    """Get the model config for a specific category (image, audio, title). Returns the first matching."""
    cursor = await db.execute(
        "SELECT key, provider, model, thinking, accept_image, accept_audio, is_default, category FROM model_configs WHERE category = ? LIMIT 1",
        (category,)
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return {"key": row[0], "provider": row[1], "model": row[2], "thinking": bool(row[3]),
            "accept_image": bool(row[4]), "accept_audio": bool(row[5]), "is_default": bool(row[6]), "category": row[7]}


# ---------- 管理员: 用户管理 ----------
async def get_all_users_db(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute("SELECT id, username, created_at FROM users ORDER BY id")
    rows = await cursor.fetchall()
    return [{"id": r[0], "username": r[1], "created_at": r[2]} for r in rows]


async def delete_user_db(db: aiosqlite.Connection, user_id: int) -> bool:
    cursor = await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    await db.commit()
    return cursor.rowcount > 0


# ---------- Token 用量 ----------
async def save_token_usage_db(db: aiosqlite.Connection, session_id: str, user_id: int,
                               model: str, prompt_tokens: int, completion_tokens: int):
    await db.execute(
        "INSERT INTO token_usage (session_id, user_id, model, prompt_tokens, completion_tokens) VALUES (?, ?, ?, ?, ?)",
        (session_id, user_id, model, prompt_tokens, completion_tokens)
    )
    await db.commit()


async def get_token_usage_stats_db(db: aiosqlite.Connection) -> dict:
    cursor = await db.execute("""
        SELECT COALESCE(SUM(prompt_tokens), 0), COALESCE(SUM(completion_tokens), 0), COUNT(*)
        FROM token_usage
    """)
    row = await cursor.fetchone()
    return {"total_prompt_tokens": row[0], "total_completion_tokens": row[1], "total_requests": row[2]}


async def get_token_usage_by_model_db(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute("""
        SELECT model, SUM(prompt_tokens), SUM(completion_tokens), COUNT(*)
        FROM token_usage GROUP BY model ORDER BY SUM(prompt_tokens + completion_tokens) DESC
    """)
    rows = await cursor.fetchall()
    return [{"model": r[0], "prompt_tokens": r[1], "completion_tokens": r[2], "requests": r[3]} for r in rows]


async def get_token_usage_by_user_db(db: aiosqlite.Connection) -> list[dict]:
    cursor = await db.execute("""
        SELECT u.username, SUM(tu.prompt_tokens), SUM(tu.completion_tokens), COUNT(*)
        FROM token_usage tu JOIN users u ON tu.user_id = u.id
        GROUP BY tu.user_id ORDER BY SUM(tu.prompt_tokens + tu.completion_tokens) DESC
    """)
    rows = await cursor.fetchall()
    return [{"username": r[0], "prompt_tokens": r[1], "completion_tokens": r[2], "requests": r[3]} for r in rows]


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
        "SELECT id, seq, idx, role, type, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at",
        (session_id,)
    )
    rows = await cursor.fetchall()
    return [
        MessageResponse(
            id=row[0],
            seq=row[1],
            idx=row[2],
            role=row[3],
            type=row[4],
            content=row[5],
            created_at=datetime.fromisoformat(row[6]),
        )
        for row in rows
    ]


def build_llm_messages(history: List[MessageResponse]) -> list[dict[str, Any]]:
    """从历史消息重建 LLM 多轮对话上下文，包含 reasoning、tool_calls、tool_result。

    当前代码在跨轮次时只加载 type=="message" 的消息，丢失了工具调用和推理内容，
    导致下一轮 LLM 不记得上一轮读过/操作过的文件内容。
    此函数从 raw messages 重建完整的 messages_for_llm 列表。
    """
    import json as _json

    messages: list[dict[str, Any]] = []
    pending: dict[str, Any] | None = None
    pending_tool_calls: list[dict[str, Any]] = []

    def _flush():
        nonlocal pending, pending_tool_calls
        if pending is None and not pending_tool_calls:
            return
        if pending is None:
            pending = {"role": "assistant"}
        if pending_tool_calls:
            pending["tool_calls"] = pending_tool_calls
        messages.append(pending)
        pending = None
        pending_tool_calls = []

    for msg in history:
        if msg.type == "message":
            if msg.role == "user":
                _flush()
                messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                if pending is None:
                    pending = {"role": "assistant"}
                pending["content"] = msg.content
        elif msg.type == "reasoning":
            if pending is None:
                pending = {"role": "assistant"}
            pending["reasoning_content"] = msg.content
        elif msg.type == "tool_call":
            if pending is None:
                pending = {"role": "assistant"}
            tc_info = _json.loads(msg.content)
            tc_id = tc_info.get("id", f"tc_{msg.id}")
            tc_name = tc_info.get("name", "")
            tc_args = tc_info.get("args", {})
            if isinstance(tc_args, dict):
                tc_args = _json.dumps(tc_args)
            pending_tool_calls.append({
                "id": tc_id,
                "type": "function",
                "function": {
                    "name": tc_name,
                    "arguments": tc_args,
                }
            })
        elif msg.type == "tool_result":
            try:
                result_data = _json.loads(msg.content)
                if isinstance(result_data, dict) and "tool_call_id" in result_data:
                    tc_id = result_data["tool_call_id"]
                    result_content = result_data.get("content", "")
                else:
                    raise _json.JSONDecodeError("Not new format", msg.content, 0)
            except (_json.JSONDecodeError, TypeError):
                tc_id = pending_tool_calls[-1]["id"] if pending_tool_calls else f"tc_{msg.id}"
                result_content = msg.content
            _flush()
            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": result_content,
            })
    _flush()
    return messages


async def get_message_db(db: aiosqlite.Connection, message_id: int) -> MessageResponse:
    cursor = await db.execute(
        "SELECT id, seq, idx, role, type, content, created_at FROM messages WHERE id = ?",
        (message_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise Exception("Message not exists")
    return MessageResponse(
        id=row[0],
        seq=row[1],
        idx=row[2],
        role=row[3],
        type=row[4],
        content=row[5],
        created_at=datetime.fromisoformat(row[6]),
    )

async def save_message_db(db: aiosqlite.Connection, session_id: str, seq: int, idx: int, role: str, type_: str,
                          content: str) -> int:
    cursor = await db.execute(
        "INSERT INTO messages (session_id, seq, idx, role, type, content) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, seq, idx, role, type_, content)
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