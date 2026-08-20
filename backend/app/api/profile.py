"""
用户画像模块 —— 用户偏好与旅行历史管理接口。

提供 /profile 下的查询、偏好更新、偏好追加以及旅行历史记录的增删查能力。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from app.db.session import get_db
from app.db.models import User
from app.services.auth import get_current_active_user
from app.services.profile import (
    get_or_create_profile,
    update_preferences,
    add_travel_history,
)

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    """偏好更新请求体模型（增量合并）。"""

    preferences: Dict[str, Any]  # 要合并进现有偏好字典的键值


class TravelHistoryItem(BaseModel):
    """旅行历史条目模型。"""

    destination: str  # 目的地
    start_date: Optional[str] = None  # 出发日期（ISO 字符串）
    end_date: Optional[str] = None  # 结束日期（ISO 字符串）
    note: Optional[str] = None  # 备注


class ProfileResponse(BaseModel):
    """用户画像响应体模型。"""

    user_id: int  # 所属用户 ID
    preferences: Dict[str, Any]  # 偏好设置
    travel_history: List[Dict[str, Any]]  # 旅行历史记录

    class Config:
        from_attributes = True  # 支持从 ORM 模型直接转换


@router.get("", response_model=ProfileResponse)
async def read_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取当前用户的画像（偏好 + 旅行历史）。

    Args:
        db: 异步数据库会话（依赖注入）。
        current_user: 当前登录用户（依赖注入）。

    Returns:
        ProfileResponse 格式的用户画像。
    """
    return await get_or_create_profile(db, current_user.id)


@router.put("/preferences", response_model=ProfileResponse)
async def update_current_preferences(
    data: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """增量更新当前用户偏好设置。

    Args:
        data: 包含待合并偏好的请求体。
        db: 异步数据库会话（依赖注入）。
        current_user: 当前登录用户（依赖注入）。

    Returns:
        更新后的用户画像。
    """
    return await update_preferences(db, current_user.id, data.preferences)


@router.post("/history", response_model=ProfileResponse)
async def add_history(
    item: TravelHistoryItem,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """向当前用户的旅行历史中添加一条记录。

    Args:
        item: 旅行历史条目（目的地、日期、备注）。
        db: 异步数据库会话（依赖注入）。
        current_user: 当前登录用户（依赖注入）。

    Returns:
        更新后的用户画像。
    """
    return await add_travel_history(
        db,
        current_user.id,
        item.model_dump(exclude_none=True),
    )