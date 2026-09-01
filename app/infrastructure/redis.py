import redis.asyncio as aioredis
import redis as sync_redis

from app.config import settings


def create_async_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


def create_sync_redis() -> sync_redis.Redis:
    return sync_redis.from_url(settings.redis_url, decode_responses=True)
