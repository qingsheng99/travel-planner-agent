"""
数据库 ORM 模型定义模块

定义所有数据库表对应的 SQLAlchemy 模型类，包括：
- User / UserProfile：用户与用户画像
- Trip：旅行行程
- Conversation：与行程关联的对话记录
- AuditLog：操作审计日志
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func
from app.db.session import Base


class User(Base):
    """用户表，存储账号与认证信息"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)       # 主键 ID
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)  # 邮箱（唯一）
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)  # 用户名（唯一）
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)          # 密码哈希值
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)                # 账号是否激活
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())  # 更新时间

    # 关联关系
    trips: Mapped[List["Trip"]] = relationship(back_populates="owner")           # 用户创建的行程列表
    profile: Mapped[Optional["UserProfile"]] = relationship(back_populates="user", uselist=False)  # 用户画像（一对一）
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")   # 用户的操作审计日志


class UserProfile(Base):
    """用户画像表，存储偏好设置与历史出行记录"""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)       # 主键 ID
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True)  # 关联用户 ID
    preferences: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)         # 偏好设置（JSON）
    travel_history: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)  # 历史出行记录（JSON 数组）
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())  # 更新时间

    user: Mapped["User"] = relationship(back_populates="profile")                 # 所属用户


class Trip(Base):
    """行程表，存储用户创建的旅行计划"""

    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)       # 主键 ID
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))        # 所属用户 ID
    title: Mapped[str] = mapped_column(String, nullable=False)                    # 行程标题
    destination: Mapped[str] = mapped_column(String, nullable=False)              # 目的地
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))  # 出发日期
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))    # 结束日期
    budget: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)             # 预算信息（JSON）
    travelers: Mapped[int] = mapped_column(Integer, default=1)                    # 出行人数
    status: Mapped[str] = mapped_column(String, default="planning")  # 行程状态：planning / planned / confirmed / completed
    itinerary: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)          # 详细行程安排（JSON）
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())  # 更新时间

    # 关联关系
    owner: Mapped["User"] = relationship(back_populates="trips")                  # 行程所属用户
    conversations: Mapped[List["Conversation"]] = relationship(back_populates="trip")  # 与行程相关的对话


class Conversation(Base):
    """对话表，存储与某个行程相关的多轮对话记录"""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)       # 主键 ID
    trip_id: Mapped[int] = mapped_column(Integer, ForeignKey("trips.id"))        # 关联行程 ID
    messages: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)    # 消息列表（JSON 数组，每条含 role / content）
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())  # 更新时间

    trip: Mapped["Trip"] = relationship(back_populates="conversations")          # 所属行程


class AuditLog(Base):
    """审计日志表，记录用户关键操作以备安全审计"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)       # 主键 ID
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)  # 操作用户 ID（可能为匿名）
    action: Mapped[str] = mapped_column(String, nullable=False)                   # 操作名称（如 login / create_trip）
    resource_type: Mapped[Optional[str]] = mapped_column(String)                  # 操作资源类型（如 "trip" / "user"）
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)       # 操作资源 ID
    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)      # 请求来源 IP
    user_agent: Mapped[Optional[str]] = mapped_column(String, nullable=True)      # 请求 User-Agent
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)            # 额外详情（JSON）
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # 记录时间

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")   # 操作用户
