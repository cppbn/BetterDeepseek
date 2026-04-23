from fastapi import APIRouter, Depends, HTTPException, status
import logging
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/models", tags=["models"])
from ChatApp.providers.models import supported_models
@router.get("")
async def get_models():
    return supported_models