"""
行程与对话服务模块

提供行程（Trip）的创建、查询、更新以及行程关联对话（Conversation）
的消息管理功能，所有操作基于异步 SQLAlchemy 会话。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Trip, Conversation
from typing import Dict, List, Optional
from datetime import datetime


async def create_trip(
    db: AsyncSession,
    user_id: int,
    title: str,
    destination: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    budget: Optional[Dict] = None,
    travelers: int = 1,
) -> Trip:
    """创建新行程并同时初始化一条关联的空白对话记录。

    参数:
        db: 异步数据库会话。
        user_id: 创建该行程的用户 ID。
        title: 行程标题。
        destination: 目的地。
        start_date: 可选，出发日期。
        end_date: 可选，结束日期。
        budget: 可选，预算配置字典。
        travelers: 出行人数，默认为 1。

    返回:
        新创建的 Trip 对象。
    """
    trip = Trip(
        user_id=user_id,
        title=title,
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        budget=budget or {},
        travelers=travelers,
        status="planning",  # 初始状态为"规划中"
        itinerary={},       # 初始行程为空
    )
    db.add(trip)
    await db.flush()

    # 为每个行程自动创建一条关联的对话记录
    conversation = Conversation(trip_id=trip.id, messages=[])
    db.add(conversation)
    await db.commit()
    await db.refresh(trip)

    return trip


async def get_trip(db: AsyncSession, trip_id: int) -> Optional[Trip]:
    """根据行程 ID 查询单条行程记录。

    参数:
        db: 异步数据库会话。
        trip_id: 行程 ID。

    返回:
        Trip 对象，未找到时返回 None。
    """
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    return result.scalar_one_or_none()


async def get_owned_trip(db: AsyncSession, trip_id: int, user_id: int) -> Optional[Trip]:
    """获取属于指定用户的行程，用于在一个查询中完成资源存在与权限校验。"""
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_trips(db: AsyncSession, user_id: int) -> List[Trip]:
    """获取指定用户的所有行程，按创建时间倒序排列。

    参数:
        db: 异步数据库会话。
        user_id: 用户 ID。

    返回:
        该用户下的 Trip 对象列表。
    """
    result = await db.execute(
        select(Trip).where(Trip.user_id == user_id).order_by(Trip.created_at.desc())
    )
    return list(result.scalars().all())


VALID_TRIP_STATUSES = ("planning", "planned", "confirmed", "completed")


async def update_trip_itinerary(db: AsyncSession, trip_id: int, itinerary: Dict) -> Optional[Trip]:
    """更新指定行程的详细行程安排，并将状态标记为"已规划"。

    参数:
        db: 异步数据库会话。
        trip_id: 行程 ID。
        itinerary: 行程安排字典（如每日行程列表）。

    返回:
        更新后的 Trip 对象，行程不存在时返回 None。
    """
    trip = await get_trip(db, trip_id)
    if trip:
        trip.itinerary = itinerary
        trip.status = "planned"  # 更新状态为"已规划"
        await db.commit()
        await db.refresh(trip)
    return trip


async def update_trip_status(
    db: AsyncSession,
    trip_id: int,
    status: str,
    user_id: int,
) -> Optional[Trip]:
    """将行程流转到指定状态，仅允许按 planning → planned → confirmed → completed 前进。

    参数:
        db: 异步数据库会话。
        trip_id: 行程 ID。
        status: 目标状态，取值 VALID_TRIP_STATUSES 之一。
        user_id: 发起操作的用户 ID（用于校验行程归属）。

    返回:
        更新后的 Trip 对象；行程不存在或无权访问返回 None。

    抛出:
        ValueError: 目标状态非法，或不是合法的正向流转。
    """
    trip = await get_owned_trip(db, trip_id, user_id)
    if trip is None:
        return None

    if status not in VALID_TRIP_STATUSES:
        raise ValueError(f"非法状态: {status}")

    from_order = VALID_TRIP_STATUSES.index(trip.status)
    to_order = VALID_TRIP_STATUSES.index(status)
    if to_order < from_order:
        raise ValueError(f"不允许从 {trip.status} 回退到 {status}")

    trip.status = status
    await db.commit()
    await db.refresh(trip)
    return trip


async def delete_trip(db: AsyncSession, trip_id: int, user_id: int) -> bool:
    """删除属于指定用户的行程及其关联对话。

    参数:
        db: 异步数据库会话。
        trip_id: 行程 ID。
        user_id: 发起删除的用户 ID（用于校验行程归属）。

    返回:
        删除成功返回 True；行程不存在或无权访问返回 False。
    """
    trip = await get_owned_trip(db, trip_id, user_id)
    if trip is None:
        return False

    # 先删除与该行程关联的对话记录，避免外键约束报错
    conversation_result = await db.execute(
        select(Conversation).where(Conversation.trip_id == trip_id)
    )
    for conversation in conversation_result.scalars().all():
        await db.delete(conversation)

    await db.delete(trip)
    await db.commit()
    return True


async def add_conversation_message(db: AsyncSession, trip_id: int, message: Dict) -> Optional[Conversation]:
    """向指定行程的对话中添加一条消息。

    参数:
        db: 异步数据库会话。
        trip_id: 行程 ID。
        message: 消息字典（通常包含 role、content 等字段）。

    返回:
        更新后的 Conversation 对象，行程不存在时返回 None。
    """
    result = await db.execute(select(Conversation).where(Conversation.trip_id == trip_id))
    conversation = result.scalar_one_or_none()
    if conversation:
        conversation.messages = [*(conversation.messages or []), message]
        await db.commit()
        await db.refresh(conversation)
    return conversation


async def get_conversation_messages(db: AsyncSession, trip_id: int) -> List[Dict]:
    """获取指定行程关联的对话消息列表。

    参数:
        db: 异步数据库会话。
        trip_id: 行程 ID。

    返回:
        消息字典列表，若无可返回空列表。
    """
    result = await db.execute(select(Conversation).where(Conversation.trip_id == trip_id))
    conversation = result.scalar_one_or_none()
    if conversation:
        return conversation.messages or []
    return []


async def persist_chat_result(
    db: AsyncSession,
    trip_id: int,
    user_message: str,
    assistant_message: str,
    itinerary: Optional[Dict] = None,
) -> None:
    """原子保存一轮对话；生成完整行程时同时更新对应 Trip。"""
    result = await db.execute(select(Conversation).where(Conversation.trip_id == trip_id))
    conversation = result.scalar_one_or_none()
    if conversation is None:
        conversation = Conversation(trip_id=trip_id, messages=[])
        db.add(conversation)

    conversation.messages = [
        *(conversation.messages or []),
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": assistant_message},
    ]

    if itinerary is not None:
        trip = await get_trip(db, trip_id)
        if trip is not None:
            trip.itinerary = itinerary
            trip.status = "planned"

    await db.commit()
