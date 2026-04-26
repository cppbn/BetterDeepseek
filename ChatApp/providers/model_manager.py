import aiosqlite
import logging
from typing import Dict, Any, Optional

from ChatApp.config import DATABASE_URL

logger = logging.getLogger(__name__)

_cache: Optional[Dict[str, Any]] = None


async def load_models_from_db() -> Dict[str, Any]:
    """Load all chat models from DB into the same format as the old supported_models dict."""
    global _cache
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT key, provider, model, thinking, accept_image, accept_audio, is_default FROM model_configs WHERE category = 'chat'"
        )
        rows = await cursor.fetchall()
    result: Dict[str, Any] = {}
    for row in rows:
        key, provider, model, thinking, accept_image, accept_audio, is_default = row
        result[key] = {
            "provider": provider,
            "model": model,
            "thinking": bool(thinking),
            "accept_image": bool(accept_image),
            "accept_audio": bool(accept_audio),
        }
        if is_default:
            result["default"] = result[key]
    _cache = result
    logger.info(f"Loaded {len(rows)} chat models from database")
    return result


async def refresh_models():
    """Refresh in-memory cache from DB. Called after admin updates."""
    await load_models_from_db()


async def get_models() -> Dict[str, Any]:
    """Get cached model configs."""
    global _cache
    if _cache is None:
        await load_models_from_db()
    return _cache or {}


async def get_image_model() -> str:
    """Get image transcription model name."""
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT model, provider FROM model_configs WHERE category = 'image' LIMIT 1"
        )
        row = await cursor.fetchone()
    return row[0] if row else "qwen/qwen3.5-flash-02-23"


async def get_audio_model() -> str:
    """Get audio transcription model name."""
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT model, provider FROM model_configs WHERE category = 'audio' LIMIT 1"
        )
        row = await cursor.fetchone()
    return row[0] if row else "xiaomi/mimo-v2.5"


async def get_title_model() -> str:
    """Get title generation model name."""
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT model FROM model_configs WHERE category = 'title' LIMIT 1"
        )
        row = await cursor.fetchone()
    return row[0] if row else "deepseek-chat"
