import aiosqlite
import httpx
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
    from ChatApp.providers.models import supported_models
    supported_models.clear()
    supported_models.update(_cache or {})
    logger.info("Refreshed supported_models from database")


async def get_models() -> Dict[str, Any]:
    """Get cached model configs."""
    global _cache
    if _cache is None:
        await load_models_from_db()
    return _cache or {}


async def sync_models_from_newapi(db: aiosqlite.Connection) -> int:
    """Fetch models from new-api /v1/models and upsert into local model_configs."""
    from ChatApp import config as cfg
    from ChatApp.database import upsert_model_config_db

    url = f"{cfg.NEWAPI_BASE_URL}/models"
    headers = {"Authorization": f"Bearer {cfg.NEWAPI_API_KEY}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    models = data.get("data", [])

    # 清理旧对话模型，避免重复
    await db.execute("DELETE FROM model_configs WHERE category = 'chat'")

    imported_count = 0
    for m in models:
        model_id = m["id"]
        parts = model_id.split("/", 1)
        if len(parts) == 2:
            provider, model_name = parts
        else:
            provider, model_name = "unknown", model_id

        key = f"{provider}/{model_name}"
        is_default = 1 if imported_count == 0 else 0

        await upsert_model_config_db(
            db, key, provider, model_name,
            True, False, False,
            is_default, "chat"
        )
        imported_count += 1

    # 自动创建缺失的特殊模型
    cursor = await db.execute("SELECT COUNT(*) FROM model_configs WHERE category = 'title'")
    if (await cursor.fetchone())[0] == 0:
        cursor = await db.execute("SELECT provider, model FROM model_configs WHERE category = 'chat' LIMIT 1")
        row = await cursor.fetchone()
        if row:
            await upsert_model_config_db(db, "title_generation", row[0], row[1], False, False, False, 0, "title")

    cursor = await db.execute("SELECT COUNT(*) FROM model_configs WHERE category = 'image'")
    if (await cursor.fetchone())[0] == 0:
        cursor = await db.execute("SELECT provider, model FROM model_configs WHERE category = 'chat' LIMIT 1")
        row = await cursor.fetchone()
        if row:
            await upsert_model_config_db(db, "image_transcription", row[0], row[1], False, False, False, 0, "image")

    cursor = await db.execute("SELECT COUNT(*) FROM model_configs WHERE category = 'audio'")
    if (await cursor.fetchone())[0] == 0:
        cursor = await db.execute("SELECT provider, model FROM model_configs WHERE category = 'chat' LIMIT 1")
        row = await cursor.fetchone()
        if row:
            await upsert_model_config_db(db, "audio_transcription", row[0], row[1], False, False, False, 0, "audio")

    await refresh_models()
    logger.info(f"Synced {imported_count} models from new-api")
    return imported_count


async def get_image_model() -> str:
    """Get image transcription model in provider/model format."""
    info = await get_image_model_info()
    if info["model"]:
        return f"{info['provider']}/{info['model']}"
    return ""


async def get_image_model_info() -> dict:
    """Get image transcription model name and provider."""
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT model, provider FROM model_configs WHERE category = 'image' LIMIT 1"
        )
        row = await cursor.fetchone()
    if row:
        return {"model": row[0], "provider": row[1]}
    return {"model": "", "provider": ""}


async def get_audio_model() -> str:
    """Get audio transcription model in provider/model format."""
    info = await get_audio_model_info()
    if info["model"]:
        return f"{info['provider']}/{info['model']}"
    return ""


async def get_audio_model_info() -> dict:
    """Get audio transcription model name and provider."""
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT model, provider FROM model_configs WHERE category = 'audio' LIMIT 1"
        )
        row = await cursor.fetchone()
    if row:
        return {"model": row[0], "provider": row[1]}
    return {"model": "", "provider": ""}


async def get_title_model() -> str:
    """Get title generation model in provider/model format."""
    async with aiosqlite.connect(DATABASE_URL) as db:
        cursor = await db.execute(
            "SELECT model, provider FROM model_configs WHERE category = 'title' LIMIT 1"
        )
        row = await cursor.fetchone()
    if row:
        return f"{row[1]}/{row[0]}"
    return ""
