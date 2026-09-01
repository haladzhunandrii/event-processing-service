from redis.asyncio import Redis

from app.infrastructure.metrics.definitions import (
    EVENT_FAILURES_KEY,
    EVENTS_PROCESSED_KEY,
    QUEUE_LAG_KEY,
)


async def record_processed(redis: Redis) -> None:
    await redis.incr(EVENTS_PROCESSED_KEY)


async def record_failure(redis: Redis) -> None:
    await redis.incr(EVENT_FAILURES_KEY)


async def set_queue_lag(redis: Redis, pending: int) -> None:
    await redis.set(QUEUE_LAG_KEY, pending)
