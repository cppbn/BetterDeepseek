from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import aiosqlite
import logging

from ChatApp.database import get_db
from ChatApp.auth import decode_access_token

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: aiosqlite.Connection = Depends(get_db)
):
    token = creds.credentials
    payload = decode_access_token(token)
    if not payload:
        logger.warning("Invalid or expired token attempt")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or Expired Token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Token")
    cursor = await db.execute("SELECT id, username FROM users WHERE id = ?", (int(user_id),))
    user = await cursor.fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not exists")
    return {"id": user[0], "username": user[1]}