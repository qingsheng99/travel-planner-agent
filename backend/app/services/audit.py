"""
审计日志服务模块

提供向 AuditLog 表写入操作审计记录的功能，用于记录用户关键操作
（注册、登录、创建行程、修改行程等），满足后续安全审计与追溯需求。
"""
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


async def write_audit_log(
    db: AsyncSession,
    action: str,
    user_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """写入一条审计日志。

    参数:
        db: 异步数据库会话（由调用方注入，保证与业务操作同事务）。
        action: 操作名称，如 "register" / "login" / "create_trip" / "save_itinerary"。
        user_id: 操作用户 ID；匿名操作可置为 None。
        resource_type: 资源类型，如 "user" / "trip"。
        resource_id: 资源 ID。
        ip_address: 请求来源 IP。
        user_agent: 请求 User-Agent。
        details: 额外详情字典（自动 JSON 序列化）。

    返回:
        新创建的 AuditLog 对象。
    """
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details or {},
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log