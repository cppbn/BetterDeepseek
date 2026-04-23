from fastapi import APIRouter, Depends, HTTPException, status
import aiosqlite
import logging

from ChatApp.pydantic_models import UserRegister, UserLogin, Token, UserInfo
from ChatApp.database import get_db, get_user_by_username, create_user
from ChatApp.auth import get_password_hash, verify_password, create_access_token
from ChatApp.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/register", response_model=Token, status_code=201)
async def register(user: UserRegister, db: aiosqlite.Connection = Depends(get_db)):
    """用户注册，成功后直接返回 token"""
    hashed = get_password_hash(user.password)
    user_id = await create_user(db, user.username, hashed)
    if not user_id:
        raise HTTPException(status_code=400, detail="Username already used")
    access_token = create_access_token(data={"sub": str(user_id)})
    logger.info(f"User '{user.username}' registered and token issued")
    return Token(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=Token)
async def login(user: UserLogin, db: aiosqlite.Connection = Depends(get_db)):
    """用户登录，返回 token"""
    db_user = await get_user_by_username(db, user.username)
    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        logger.warning(f"Failed login attempt for username: {user.username}")
        raise HTTPException(status_code=401, detail="Wrong Username or Password")
    access_token = create_access_token(data={"sub": str(db_user["id"])})
    logger.info(f"User '{user.username}' logged in successfully")
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前登录用户的信息"""
    logger.info(f"User info requested for user_id={current_user['id']}")
    return UserInfo(id=current_user["id"], username=current_user["username"])