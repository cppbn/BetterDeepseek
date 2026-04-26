from fastapi import APIRouter, HTTPException, status, Security, Depends, Body, Query
from fastapi.security import APIKeyHeader
import aiosqlite
import logging
from pydantic import BaseModel
from typing import Optional

from ChatApp import config
from ChatApp.database import (
    get_db, get_all_model_configs_db, get_model_config_db, upsert_model_config_db,
    delete_model_config_db, get_all_users_db, delete_user_db,
    get_token_usage_stats_db, get_token_usage_by_model_db, get_token_usage_by_user_db
)
from ChatApp.providers.model_manager import refresh_models

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])

api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)

ALLOWED_KEYS = {
    "DEEPSEEK_API_KEY",
    "TAVILY_API_KEY",
    "OPENROUTER_API_KEY",
    "SYSTEM_PROMPT_DEFAULT",
    "SYSTEM_PROMPT_WITH_CODE_EXEC",
}

# --- Pydantic models ---
class ModelConfigIn(BaseModel):
    key: str
    provider: str
    model: str
    thinking: bool = False
    accept_image: bool = False
    accept_audio: bool = False
    is_default: bool = False
    category: str = "chat"

class EnvValue(BaseModel):
    value: str


class VerifyIn(BaseModel):
    key: str


async def verify_admin_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != config.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin API key",
        )
    return True


# ===================== Verify =====================

@router.post("/verify")
async def verify_key(body: VerifyIn):
    if not body.key or body.key != config.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin API key")
    return {"valid": True}


# ===================== Env / Prompts =====================

@router.get("/env/{key}", dependencies=[Depends(verify_admin_key)])
async def get_env(key: str):
    if key not in ALLOWED_KEYS:
        raise HTTPException(status_code=404, detail=f"Configuration key '{key}' is not allowed.")
    value = getattr(config, key, None)
    return {"key": key, "value": value}


@router.post("/env/{key}", dependencies=[Depends(verify_admin_key)])
async def set_env(key: str, body: EnvValue):
    if key not in ALLOWED_KEYS:
        raise HTTPException(status_code=404, detail=f"Cannot modify configuration key '{key}'.")
    setattr(config, key, body.value)
    logger.warning(f"Admin updated env key '{key}' to new value (length={len(body.value)})")
    return {"key": key, "message": "Configuration updated successfully (in-memory only)."}


@router.get("/env", dependencies=[Depends(verify_admin_key)])
async def list_env():
    return [{"key": k, "value": getattr(config, k, None)} for k in sorted(ALLOWED_KEYS)]


# ===================== Model Configs =====================

@router.get("/models", dependencies=[Depends(verify_admin_key)])
async def list_models(db: aiosqlite.Connection = Depends(get_db)):
    return await get_all_model_configs_db(db)


@router.get("/models/{key}", dependencies=[Depends(verify_admin_key)])
async def get_model(key: str, db: aiosqlite.Connection = Depends(get_db)):
    model = await get_model_config_db(db, key)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{key}' not found")
    return model


@router.put("/models/{key}", dependencies=[Depends(verify_admin_key)])
async def upsert_model(key: str, body: ModelConfigIn, db: aiosqlite.Connection = Depends(get_db)):
    if key != body.key:
        raise HTTPException(status_code=400, detail="Key in path must match key in body")
    await upsert_model_config_db(db, body.key, body.provider, body.model,
                                  int(body.thinking), int(body.accept_image),
                                  int(body.accept_audio), int(body.is_default), body.category)
    await refresh_models()
    logger.info(f"Admin upserted model config: {key}")
    return {"message": f"Model '{key}' saved"}


@router.delete("/models/{key}", dependencies=[Depends(verify_admin_key)])
async def delete_model(key: str, db: aiosqlite.Connection = Depends(get_db)):
    if not await delete_model_config_db(db, key):
        raise HTTPException(status_code=404, detail=f"Model '{key}' not found")
    await refresh_models()
    logger.info(f"Admin deleted model config: {key}")
    return {"message": f"Model '{key}' deleted"}


# ===================== Users =====================

@router.get("/users", dependencies=[Depends(verify_admin_key)])
async def list_users(db: aiosqlite.Connection = Depends(get_db)):
    return await get_all_users_db(db)


@router.delete("/users/{user_id}", dependencies=[Depends(verify_admin_key)])
async def delete_user(user_id: int, db: aiosqlite.Connection = Depends(get_db)):
    if not await delete_user_db(db, user_id):
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    logger.info(f"Admin deleted user {user_id}")
    return {"message": f"User {user_id} deleted"}


# ===================== Token Usage =====================

@router.get("/token-usage", dependencies=[Depends(verify_admin_key)])
async def token_usage_stats(db: aiosqlite.Connection = Depends(get_db)):
    summary = await get_token_usage_stats_db(db)
    by_model = await get_token_usage_by_model_db(db)
    by_user = await get_token_usage_by_user_db(db)
    return {"summary": summary, "by_model": by_model, "by_user": by_user}
