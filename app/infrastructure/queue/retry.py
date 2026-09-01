import time

from redis.asyncio import Redis

from app.config import settings
from app.infrastructure.metrics.definitions import RETRY_PREFIX


def compute_backoff(attempts: int) -> int:
    return min(2 ** min(attempts, 6), settings.max_backoff_seconds)


async def should_attempt(redis: Redis, message_id: str) -> bool:
    return time.time() >= float(await redis.hget(RETRY_PREFIX + message_id, "next_at") or 0)


async def record_failure(redis: Redis, message_id: str) -> int:
    key = RETRY_PREFIX + message_id
    attempts = await redis.hincrby(key, "attempts", 1)
    delay = compute_backoff(attempts)
    await redis.hset(key, mapping={"next_at": time.time() + delay})
    await redis.expire(key, 86400)
    return attempts


async def clear_retry_state(redis: Redis, message_id: str) -> None:
    await redis.delete(RETRY_PREFIX + message_id)
