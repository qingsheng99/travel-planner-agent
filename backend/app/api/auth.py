"""
认证模块 —— 用户注册、登录及获取当前用户信息接口。

提供 /auth/register（注册）、/auth/login（登录）、/auth/me（获取当前用户）三个端点。
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from pydantic import BaseModel, EmailStr
from app.db.session import get_db
from app.db.models import User
from app.services.audit import write_audit_log
from app.services.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_current_active_user,
)
from app.schemas.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class UserCreate(BaseModel):
    """用户注册请求体模型。"""

    email: EmailStr  # 用户邮箱
    username: str  # 用户名
    password: str  # 明文密码（服务端会哈希存储）


class UserResponse(BaseModel):
    """用户信息响应体模型。"""

    id: int  # 用户 ID
    email: str  # 用户邮箱
    username: str  # 用户名

    class Config:
        from_attributes = True  # 支持从 ORM 模型直接转换


class Token(BaseModel):
    """JWT Token 响应体模型。"""

    access_token: str  # JWT 访问令牌
    token_type: str  # 令牌类型（固定为 "bearer"）


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """用户注册接口。

    校验邮箱和用户名是否已被占用，若通过则创建新用户并写入审计日志。

    Args:
        user_data: 注册请求体，包含 email、username、password。
        request: 当前 HTTP 请求（用于记录审计日志）。
        db: 异步数据库会话（由 FastAPI 依赖注入）。

    Returns:
        创建成功的用户对象（UserResponse 格式）。

    Raises:
        HTTPException 400: 邮箱或用户名已被注册。
    """
    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    # 创建新用户并持久化到数据库
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),  # 密码哈希后存储
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)  # 刷新以获取数据库自动生成的字段（如 id）
    await write_audit_log(
        db=db,
        action="register",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={"username": user.username},
    )
    return user


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """用户登录接口。

    验证邮箱和密码，成功后返回 JWT 访问令牌并写入审计日志。

    Args:
        request: 当前 HTTP 请求（用于记录审计日志）。
        form_data: OAuth2 表单格式的登录凭据（username / password）。
        db: 异步数据库会话（由 FastAPI 依赖注入）。

    Returns:
        包含 access_token 和 token_type 的 Token 响应。

    Raises:
        HTTPException 401: 邮箱或密码错误。
    """
    # 验证用户凭据
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 生成 JWT 令牌，过期时间由配置决定
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    await write_audit_log(
        db=db,
        action="login",
        user_id=user.id,
        resource_type="user",
        resource_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """获取当前登录用户信息。

    Args:
        current_user: 由 JWT 令牌解析出的当前用户对象（依赖注入）。

    Returns:
        当前用户对象（UserResponse 格式）。
    """
    return current_user