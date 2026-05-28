from fastapi import APIRouter, Depends, HTTPException, status
import aiosqlite
import logging
from pydantic import BaseModel
from typing import Optional

from ChatApp.database import get_db, get_dev_settings_db, upsert_dev_settings_db
from ChatApp.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dev", tags=["Developer"])


class DevSettings(BaseModel):
    system_prompt_default: Optional[str] = None
    system_prompt_with_code_exec: Optional[str] = None
    sandbox_network_disabled: Optional[bool] = None
    sandbox_idle_timeout: Optional[int] = None


@router.get("/settings")
async def get_settings(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    if current_user.get("role") != "developer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Developer access required")
    settings = await get_dev_settings_db(db, current_user["id"])
    if not settings:
        return {
            "system_prompt_default": None,
            "system_prompt_with_code_exec": None,
            "sandbox_network_disabled": True,
            "sandbox_idle_timeout": 3600,
        }
    return settings


@router.put("/settings")
async def update_settings(
    body: DevSettings,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    if current_user.get("role") != "developer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Developer access required")
    await upsert_dev_settings_db(
        db,
        user_id=current_user["id"],
        system_prompt_default=body.system_prompt_default,
        system_prompt_with_code_exec=body.system_prompt_with_code_exec,
        sandbox_network_disabled=body.sandbox_network_disabled,
        sandbox_idle_timeout=body.sandbox_idle_timeout,
    )
    return {"message": "Developer settings updated"}
