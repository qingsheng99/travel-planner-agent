"""
Redis 缓存工具模块

提供异步 Redis 客户端（懒加载单例）及通用的缓存读写接口，
支持 JSON 序列化 / 反序列化、自定义 TTL 和键名生成。
"""
import redis.asyncio as aioredis
from typing import Optional, Any
import json
from app.schemas.config import settings

# 全局 Redis 客户端实例（懒加载，首次调用 get_redis() 时初始化）
_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """
    获取 Redis 异步客户端（懒加载单例）

    首次调用时根据配置创建连接，后续复用已有实例。

    Returns:
        aioredis.Redis: Redis 异步客户端实例
    """
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,  # 自动将字节响应解码为字符串
        )
    return _redis


async def close_redis():
    """
    关闭 Redis 连接

    释放全局 Redis 客户端实例，将 _redis 置为 None 以便后续重新初始化。
    """
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


async def cache_get(key: str) -> Optional[Any]:
    """
    从缓存读取数据

    Args:
        key: 缓存键名

    Returns:
        缓存值（自动反序列化 JSON），若键不存在则返回 None
    """
    r = await get_redis()
    value = await r.get(key)
    if value is not None:
        try:
            # 尝试 JSON 反序列化，非 JSON 字符串则原样返回
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return None


async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """
    写入缓存

    Args:
        key:   缓存键名
        value: 缓存值（非字符串类型自动 JSON 序列化）
        ttl:   过期时间（秒），未指定时使用配置中的默认值 REDIS_CACHE_TTL
    """
    r = await get_redis()
    ttl = ttl or settings.REDIS_CACHE_TTL
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False)
    await r.setex(key, ttl, value)


async def cache_delete(key: str) -> None:
    """
    删除缓存

    Args:
        key: 要删除的缓存键名
    """
    r = await get_redis()
    await r.delete(key)


def cache_key(*parts: str) -> str:
    """
    生成缓存键名

    将多个部分用冒号连接，形成层级结构的键名，便于管理。
    例如：cache_key("user", "123", "profile") → "user:123:profile"

    Args:
        *parts: 键名各部分

    Returns:
        str: 拼接后的缓存键
    """
    return ":".join(parts)