from fastapi import APIRouter, HTTPException, status, Security, Depends, Body
from fastapi.security import APIKeyHeader
import logging
from ChatApp import config  # 导入 config 模块以修改模块级变量

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])

api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)

# 可动态修改的配置项白名单
ALLOWED_KEYS = {
    "DEEPSEEK_API_KEY",
    "TAVILY_API_KEY",
    "OPENROUTER_API_KEY",
    "SYSTEM_PROMPT_DEFAULT",
    "SYSTEM_PROMPT_WITH_CODE_EXEC",
}


async def verify_admin_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key != config.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin API key",
        )
    return True


@router.get("/env/{key}", dependencies=[Depends(verify_admin_key)])
async def get_env(key: str):
    """
    获取指定配置项当前的值。
    仅返回白名单中的键，否则返回 404。
    """
    if key not in ALLOWED_KEYS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration key '{key}' is not allowed or does not exist.",
        )

    value = getattr(config, key, None)
    logger.info(f"Admin fetched env key '{key}'")
    return {"key": key, "value": value}


@router.post("/env/{key}", dependencies=[Depends(verify_admin_key)])
async def set_env(
    key: str,
    value: str = Body(..., embed=True),  # 从请求体接收 JSON: {"value": "..."}
):
    """
    更新指定配置项的值（仅更新内存中的配置，重启后失效）。
    只允许修改白名单中的键。
    """
    if key not in ALLOWED_KEYS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot modify configuration key '{key}'. It is not allowed.",
        )

    # 更新 config 模块的全局变量
    setattr(config, key, value)
    logger.warning(f"Admin updated env key '{key}' to new value (length={len(value)})")
    return {"key": key, "message": "Configuration updated successfully (in-memory only)."}