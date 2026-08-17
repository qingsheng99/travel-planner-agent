import redis.asyncio as aioredis
from typing import Optional, Any
import json
from app.schemas.config import settings

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """获取 Redis 异步客户端（懒加载单例）"""
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
        )
    return _redis


async def close_redis():
    """关闭 Redis 连接"""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None


async def cache_get(key: str) -> Optional[Any]:
    """从缓存读取"""
    r = await get_redis()
    value = await r.get(key)
    if value is not None:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return None


async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """写入缓存"""
    r = await get_redis()
    ttl = ttl or settings.REDIS_CACHE_TTL
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False)
    await r.setex(key, ttl, value)


async def cache_delete(key: str) -> None:
    """删除缓存"""
    r = await get_redis()
    await r.delete(key)


def cache_key(*parts: str) -> str:
    """生成缓存键"""
    return ":".join(parts)