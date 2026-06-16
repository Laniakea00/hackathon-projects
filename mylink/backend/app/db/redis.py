import redis.asyncio as redis
from typing import Optional
from app.config import settings

redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """
    Get Redis client instance
    """
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_client


async def close_redis():
    """
    Close Redis connection
    """
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None

