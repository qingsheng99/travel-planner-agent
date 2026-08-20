"""
用户画像服务模块

管理用户个人偏好与旅行历史记录，提供用户画像（UserProfile）
的查询、创建、偏好更新和旅行历史追加等操作。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import UserProfile
from typing import Dict, Optional


async def get_user_profile(db: AsyncSession, user_id: int) -> Optional[UserProfile]:
    """根据用户 ID 查询用户画像。

    参数:
        db: 异步数据库会话。
        user_id: 用户 ID。

    返回:
        UserProfile 对象，未找到时返回 None。
    """
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    return result.scalar_one_or_none()


async def get_or_create_profile(db: AsyncSession, user_id: int) -> UserProfile:
    """获取用户画像，若不存在则自动创建一条默认画像。"""
    profile = await get_user_profile(db, user_id)
    if profile is None:
        profile = await create_user_profile(db, user_id)
    return profile


async def create_user_profile(db: AsyncSession, user_id: int) -> UserProfile:
    """为指定用户创建默认的用户画像记录。

    初始偏好为空字典，旅行历史为空列表。

    参数:
        db: 异步数据库会话。
        user_id: 用户 ID。

    返回:
        新创建的 UserProfile 对象。
    """
    profile = UserProfile(user_id=user_id, preferences={}, travel_history=[])
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def update_preferences(db: AsyncSession, user_id: int, preferences: Dict) -> UserProfile:
    """更新用户偏好设置。若用户画像不存在则自动创建。

    将传入的偏好字典合并到已有偏好中（增量更新）。

    参数:
        db: 异步数据库会话。
        user_id: 用户 ID。
        preferences: 要更新的偏好键值对字典。

    返回:
        更新后的 UserProfile 对象。
    """
    profile = await get_user_profile(db, user_id)
    if not profile:
        profile = await create_user_profile(db, user_id)  # 不存在则新建

    profile.preferences = {**(profile.preferences or {}), **preferences}

    await db.commit()
    await db.refresh(profile)
    return profile


async def add_travel_history(db: AsyncSession, user_id: int, trip_data: Dict) -> UserProfile:
    """向用户画像的旅行历史记录中添加一条行程数据。

    若用户画像不存在则自动创建。

    参数:
        db: 异步数据库会话。
        user_id: 用户 ID。
        trip_data: 要添加的行程数据字典（如目的地、日期等信息）。

    返回:
        更新后的 UserProfile 对象。
    """
    profile = await get_user_profile(db, user_id)
    if not profile:
        profile = await create_user_profile(db, user_id)  # 不存在则新建

    profile.travel_history = [*(profile.travel_history or []), trip_data]

    await db.commit()
    await db.refresh(profile)
    return profile
