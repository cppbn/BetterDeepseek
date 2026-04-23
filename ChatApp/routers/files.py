from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
import aiosqlite
import aiofiles
import os
import uuid
import logging

from ChatApp.database import get_db, session_belongs_to_user, save_file_record_db, get_file_record_db
from ChatApp.dependencies import get_current_user
from ChatApp.config import UPLOAD_DIR
from ChatApp.pydantic_models import FileInfo
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions/{session_id}/files", tags=["files"])


@router.post("")
async def upload_file(
    session_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """上传文件到指定会话"""
    if not await session_belongs_to_user(db, session_id, current_user["id"]):
        logger.warning(f"Unauthorized file upload attempt to session {session_id}")
        raise HTTPException(status_code=404, detail="Session not exists or Unauthenticated")

    file_id = str(uuid.uuid4())
    original_filename = file.filename or "unnamed"
    ext = os.path.splitext(original_filename)[1] or ""
    stored_filename = f"{file_id}{ext}"
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    file_path = os.path.join(session_dir, stored_filename)

    try:
        async with aiofiles.open(file_path, "wb") as buffer:
            content = await file.read()
            file_size = len(content)
            await buffer.write(content)
    except Exception as e:
        logger.error(f"Failed to save file {original_filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    await save_file_record_db(
        db, file_id, session_id, None,
        original_filename, stored_filename, file_path, file_size,
        file.content_type or "application/octet-stream"
    )

    logger.info(f"File uploaded: {original_filename} (id={file_id}) to session {session_id}")
    return {"file_id": file_id, "original_filename": original_filename, "file_size": file_size}


@router.get("/{file_id}")
async def download_file(
    session_id: str,
    file_id: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """下载指定会话中的文件"""
    if not await session_belongs_to_user(db, session_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Session not exists or Unauthenticated")

    file_info = await get_file_record_db(db, file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not exists")

    if not os.path.exists(file_info["file_path"]):
        logger.error(f"File missing on disk: {file_info['file_path']}")
        raise HTTPException(status_code=404, detail="File already lost")

    logger.info(f"File download: {file_info['original_filename']} (id={file_id})")
    return FileResponse(
        path=file_info["file_path"],
        filename=file_info["original_filename"],
        media_type=file_info["mime_type"]
    )

@router.get("/{file_id}/metadata", response_model=FileInfo)
async def get_file_metadata(
    session_id: str,
    file_id: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """获取文件元信息"""
    if not await session_belongs_to_user(db, session_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Session not exists or Unauthenticated")

    file_info = await get_file_record_db(db, file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not exists")

    # 仅返回前端需要的字段（避免暴露内部路径）
    return {
        "file_id": file_info["id"],
        "original_filename": file_info["original_filename"],
        "file_size": file_info["file_size"],
        "mime_type": file_info["mime_type"]
    }