from redis.asyncio import Redis

from app.config import settings
from app.domain.schemas import TransactionEvent


async def enqueue_event(redis: Redis, event: TransactionEvent) -> str:
    return await redis.xadd(settings.stream_name, {"event": event.model_dump_json()})
