"""
行程管理模块 —— 行程的增删改查接口。

提供 /trips/ 下的创建、列表、详情查询及行程单更新功能。
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
from app.db.session import get_db
from app.db.models import User
from app.services.auth import get_current_active_user
from app.services.audit import write_audit_log
from app.services.itinerary import (
    create_trip,
    get_owned_trip,
    get_user_trips,
    delete_trip,
    update_trip_itinerary,
    update_trip_status,
    VALID_TRIP_STATUSES,
)

router = APIRouter(prefix="/trips", tags=["trips"])


class TripCreate(BaseModel):
    """创建行程的请求体模型。"""

    title: str  # 行程标题
    destination: str  # 目的地
    start_date: Optional[datetime] = None  # 开始日期（可选）
    end_date: Optional[datetime] = None  # 结束日期（可选）
    budget: Optional[Dict] = None  # 预算信息（可选，JSON 格式）
    travelers: int = 1  # 出行人数，默认为 1


class TripResponse(BaseModel):
    """行程信息响应体模型。"""

    id: int  # 行程 ID
    title: str  # 行程标题
    destination: str  # 目的地
    start_date: Optional[datetime]  # 开始日期
    end_date: Optional[datetime]  # 结束日期
    budget: Dict  # 预算信息
    travelers: int  # 出行人数
    status: str  # 行程状态（如 planning / confirmed / completed）
    itinerary: Dict  # 详细行程单（JSON 格式）
    created_at: datetime  # 创建时间
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # 支持从 ORM 模型直接转换


@router.post("", response_model=TripResponse)
async def create_new_trip(
    trip_data: TripCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建新行程。

    调用服务层 create_trip 函数，将行程数据持久化到数据库，
    并写入一条创建行程的审计日志。

    Args:
        trip_data: 行程创建请求体。
        request: 当前 HTTP 请求（用于获取 IP 与 User-Agent，记录审计日志）。
        db: 异步数据库会话（依赖注入）。
        current_user: 当前登录用户（依赖注入）。

    Returns:
        创建成功的行程对象（TripResponse 格式）。
    """
    trip = await create_trip(
        db=db,
        user_id=current_user.id,
        title=trip_data.title,
        destination=trip_data.destination,
        start_date=trip_data.start_date,
        end_date=trip_data.end_date,
        budget=trip_data.budget,
        travelers=trip_data.travelers,
    )
    await write_audit_log(
        db=db,
        action="create_trip",
        user_id=current_user.id,
        resource_type="trip",
        resource_id=trip.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={"title": trip.title, "destination": trip.destination},
    )
    return trip


@router.get("", response_model=List[TripResponse])
async def list_trips(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取当前用户的所有行程列表。

    Args:
        db: 异步数据库会话（依赖注入）。
        current_user: 当前登录用户（依赖注入）。

    Returns:
        当前用户的所有行程列表。
    """
    return await get_user_trips(db, current_user.id)


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip_detail(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取单个行程的详细信息。

    先校验行程是否存在，再校验当前用户是否有权限访问。

    Args:
        trip_id: 行程 ID（路径参数）。
        db: 异步数据库会话（依赖注入）。
        current_user: 当前登录用户（依赖注入）。

    Returns:
        行程详情对象（TripResponse 格式）。

    Raises:
        HTTPException 404: 行程不存在。
        HTTPException 403: 无权访问该行程。
    """
    trip = await get_owned_trip(db, trip_id, current_user.id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


class TripStatusUpdate(BaseModel):
    """行程状态更新请求体模型。"""

    status: str  # 目标状态：planning / planned / confirmed / completed


@router.put("/{trip_id}/status", response_model=TripResponse)
async def change_trip_status(
    trip_id: int,
    data: TripStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """流转行程状态（仅允许正向流转）。

    Args:
        trip_id: 行程 ID（路径参数）。
        data: 目标状态请求体。
        request: 当前 HTTP 请求（用于记录审计日志）。
        db: 异步数据库会话（依赖注入）。
        current_user: 当前登录用户（依赖注入）。

    Returns:
        更新后的行程对象（TripResponse 格式）。

    Raises:
        HTTPException 404: 行程不存在或无权访问。
        HTTPException 400: 目标状态非法或不允许回退。
    """
    try:
        trip = await update_trip_status(db, trip_id, data.status, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    await write_audit_log(
        db=db,
        action="update_trip_status",
        user_id=current_user.id,
        resource_type="trip",
        resource_id=trip_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details={"status": data.status},
    )
    return trip


@router.put("/{trip_id}/itinerary", response_model=TripResponse)
async def save_itinerary(
    trip_id: int,
    itinerary: Dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """保存或更新行程的详细行程单。

    先校验行程是否存在及当前用户是否有权限，再调用服务层更新行程单，
    并写入一条修改行程的审计日志。

    Args:
        trip_id: 行程 ID（路径参数）。
        itinerary: 行程单数据（JSON 格式，请求体）。
        request: 当前 HTTP 请求（用于记录审计日志）。
        db: 异步数据库会话（依赖注入）。
        current_user: 当前登录用户（依赖注入）。

    Returns:
        更新后的行程对象（TripResponse 格式）。

    Raises:
        HTTPException 404: 行程不存在。
        HTTPException 403: 无权修改该行程。
    """
    trip = await get_owned_trip(db, trip_id, current_user.id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    updated_trip = await update_trip_itinerary(db, trip_id, itinerary)
    await write_audit_log(
        db=db,
        action="save_itinerary",
        user_id=current_user.id,
        resource_type="trip",
        resource_id=trip_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return updated_trip


@router.delete("/{trip_id}", status_code=204)
async def remove_trip(
    trip_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除指定行程及其关联对话。

    校验行程归属后删除，并写入一条删除行程的审计日志。

    Args:
        trip_id: 行程 ID（路径参数）。
        request: 当前 HTTP 请求（用于记录审计日志）。
        db: 异步数据库会话（依赖注入）。
        current_user: 当前登录用户（依赖注入）。

    Raises:
        HTTPException 404: 行程不存在。
        HTTPException 403: 无权删除该行程。
    """
    deleted = await delete_trip(db, trip_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trip not found")

    await write_audit_log(
        db=db,
        action="delete_trip",
        user_id=current_user.id,
        resource_type="trip",
        resource_id=trip_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
