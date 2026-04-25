from fastapi import APIRouter, Depends, HTTPException, status
import aiosqlite
import os
import logging
import asyncio
from typing import List

from ChatApp.pydantic_models import SessionCreateResponse, SessionInfo, MessageResponse, FileInfo
from ChatApp.database import get_db, create_session_db, get_sessions_db, session_belongs_to_user, get_messages_db, get_message_db, get_message_attachments_db
from ChatApp.dependencies import get_current_user
from ChatApp.tools.sandbox import stop_sandbox
from ChatApp.config import UPLOAD_DIR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# 运行中的沙箱字典（会话 -> 容器ID）
running_sandboxes = {}
aiolock = asyncio.Lock()


@router.post("", response_model=SessionCreateResponse, status_code=201)
async def create_session(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """创建新对话会话"""
    session_id = await create_session_db(db, current_user["id"])
    logger.info(f"Session {session_id} created for user {current_user['username']}")
    return SessionCreateResponse(session_id=session_id)


@router.get("", response_model=list[SessionInfo])
async def list_sessions(
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """获取当前用户的所有会话"""
    sessions = await get_sessions_db(db, current_user["id"])
    logger.info(f"Listed {len(sessions)} sessions for user {current_user['username']}")
    return sessions

@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """获取某个会话的消息历史（需验证所有权）"""
    try:
        messages = await get_messages_db(db, session_id, current_user["id"])
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
    return messages

@router.get("/{session_id}/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    session_id: str,
    message_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """获取会话的某个消息（需验证所有权）"""
    if not await session_belongs_to_user(db, session_id, current_user["id"]):
        raise HTTPException(status_code=401, detail="Unauthitcated")
    try:
        message = await get_message_db(db, message_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    logger.info(f"Retrieved {message}for session {session_id}")
    return message

@router.get("/{session_id}/messages/{message_id}/attachments",response_model=List[FileInfo])
async def get_message_attachments(
    session_id: str,
    message_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """获取消息的附件（需验证所有权）"""
    if not await session_belongs_to_user(db, session_id, current_user["id"]):
        raise HTTPException(status_code=401, detail="Unauthitcated")
    attachments = await get_message_attachments_db(db, session_id, message_id)
    if not attachments:
        return []
    return [
        FileInfo(
            file_id=att["id"],
            original_filename=att["original_filename"],
            file_size=att["file_size"],
            mime_type=att["mime_type"],
        )
        for att in attachments
    ]

@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """删除指定会话，并清理所有关联资源"""
    if not await session_belongs_to_user(db, session_id, current_user["id"]):
        logger.warning(f"Unauthorized attempt to delete session {session_id} by user {current_user['id']}")
        raise HTTPException(status_code=404, detail="Session not exists or Unauthenticated")

    # 1. 获取该会话所有文件的物理路径
    cursor = await db.execute("SELECT file_path FROM files WHERE session_id = ?", (session_id,))
    file_paths = [row[0] for row in await cursor.fetchall()]

    # 2. 停止并移除关联的沙箱容器
    container_id = running_sandboxes.get(session_id)
    if container_id:
        try:
            await stop_sandbox(container_id)
            logger.info(f"Stopped sandbox container {container_id} for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to clean up sandbox container {container_id}: {e}")
        finally:
            async with aiolock:
                running_sandboxes.pop(session_id, None)

    # 3. 删除物理文件
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Deleted file: {path}")
        except Exception as e:
            logger.warning(f"Failed to delete file {path}: {e}")

    # 4. 删除数据库记录（外键级联自动删除 messages 和 files）
    await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    await db.commit()

    # 5. 删除会话专属上传目录
    session_upload_dir = os.path.join(UPLOAD_DIR, session_id)
    try:
        if os.path.exists(session_upload_dir) and not os.listdir(session_upload_dir):
            os.rmdir(session_upload_dir)
            logger.info(f"Removed empty upload directory: {session_upload_dir}")
    except Exception as e:
        logger.warning(f"Failed to remove upload directory {session_upload_dir}: {e}")

    logger.info(f"Session {session_id} deleted successfully")
    return {"status": "deleted", "session_id": session_id}

@router.delete("/{session_id}/messages/{message_id}")
async def delete_message(
    session_id: str,
    message_id: int,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """删除指定消息及其后续消息，并清理所有关联资源"""
    if not await session_belongs_to_user(db, session_id, current_user["id"]):
        logger.warning(f"Unauthorized attempt to delete session {session_id} by user {current_user['id']}")
        raise HTTPException(status_code=404, detail="Session not exists or Unauthenticated")
    
    files_cursor = await db.execute("SELECT file_path FROM files WHERE session_id = ? AND message_id >= ?",(session_id, message_id,))
    rows = await files_cursor.fetchall()
    file_paths = [row[0] for row in rows]

    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Deleted file: {path}")
        except Exception as e:
            logger.warning(f"Failed to delete file {path}: {e}")
    
    delete_cursor = await db.execute("DELETE FROM messages WHERE session_id = ? AND id >= ?", (session_id, message_id,))
    await db.commit()

    return {"status": "deleted", "count": delete_cursor.rowcount}