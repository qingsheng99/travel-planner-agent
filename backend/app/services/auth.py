"""
认证与授权服务模块

提供用户密码哈希验证、JWT 令牌生成与解析、以及当前用户身份
获取等核心认证功能，基于 FastAPI 依赖注入体系实现。
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt  # JWT 编解码库
from passlib.context import CryptContext  # 密码哈希上下文
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.config import settings
from app.db.session import get_db
from app.db.models import User

# bcrypt 密码加密上下文，用于对密码进行哈希和验签
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# OAuth2 密码模式的 Bearer token 认证方案，自动从请求头中提取 token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希密码是否匹配。

    参数:
        plain_password: 用户输入的明文密码。
        hashed_password: 数据库中存储的哈希密码。

    返回:
        匹配返回 True，否则返回 False。
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """对明文密码进行 bcrypt 哈希处理。

    参数:
        password: 用户原始明文密码。

    返回:
        哈希后的密码字符串。
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT 访问令牌。

    参数:
        data: 要编码到令牌中的负载数据（如 {"sub": user.email}）。
        expires_delta: 可选的过期时间增量，未指定时使用配置的默认过期时间。

    返回:
        编码后的 JWT 字符串。
    """
    to_encode = data.copy()
    # 计算过期时间：当前 UTC 时间 + 指定的增量或默认过期时长
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})  # 将过期时间写入令牌负载
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """根据邮箱查询用户。

    参数:
        db: 异步数据库会话。
        email: 用户邮箱地址。

    返回:
        匹配的 User 对象，未找到则返回 None。
    """
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """根据用户名查询用户。

    参数:
        db: 异步数据库会话。
        username: 用户名。

    返回:
        匹配的 User 对象，未找到则返回 None。
    """
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """验证用户邮箱和密码，完成登录认证。

    参数:
        db: 异步数据库会话。
        email: 用户邮箱地址。
        password: 用户明文密码。

    返回:
        认证成功返回 User 对象，失败返回 None。
    """
    user = await get_user_by_email(db, email)
    if not user:
        return None  # 用户不存在
    if not verify_password(password, user.hashed_password):
        return None  # 密码错误
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从请求中解析 JWT 令牌并获取当前用户（FastAPI 依赖注入用）。

    从请求的 Authorization 头中提取 Bearer token，解码后提取邮箱
    信息，再查询数据库得到对应用户。

    参数:
        token: 从请求中自动提取的 JWT 令牌。
        db: 从依赖注入中获取的异步数据库会话。

    返回:
        当前认证的 User 对象。

    异常:
        HTTPException 401: 令牌无效、过期或用户不存在时抛出。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")  # 从令牌负载中提取邮箱
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户（在 get_current_user 基础上额外检查账户是否激活）。

    参数:
        current_user: 由 get_current_user 依赖注入获得的 User 对象。

    返回:
        当前活跃的 User 对象。

    异常:
        HTTPException 400: 用户账户未激活时抛出。
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user