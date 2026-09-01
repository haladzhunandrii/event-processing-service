import asyncio
from typing import Any

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError
from sqlalchemy.exc import DBAPIError, OperationalError

from app.config import settings
from app.domain.exceptions import UnsupportedCurrency
from app.domain.schemas import TransactionEvent
from app.infrastructure.database import SessionLocal
from app.infrastructure.metrics import recorder
from app.infrastructure.queue.dlq import move_to_dlq
from app.infrastructure.queue.retry import clear_retry_state, record_failure, should_attempt
from app.services.processor import store_event

TRANSIENT_ERRORS = (OperationalError, DBAPIError, RedisConnectionError, TimeoutError, OSError)


def process_event_sync(event: TransactionEvent) -> bool:
    with SessionLocal() as session:
        return store_event(session, event)


async def handle_message(redis: Redis, message_id: str, fields: dict[str, Any]) -> bool:
    """Process one stream message. Returns True when work was attempted (not skipped by backoff)."""
    if not await should_attempt(redis, message_id):
        return False

    try:
        event = TransactionEvent.model_validate_json(fields["event"])
    except ValidationError as error:
        await move_to_dlq(redis, message_id, fields, f"validation_error: {error}")
        await redis.xack(settings.stream_name, settings.consumer_group, message_id)
        await clear_retry_state(redis, message_id)
        return True

    try:
        inserted = await asyncio.to_thread(process_event_sync, event)
        await redis.xack(settings.stream_name, settings.consumer_group, message_id)
        await clear_retry_state(redis, message_id)
        if inserted:
            await recorder.record_processed(redis)
        return True
    except UnsupportedCurrency as error:
        await move_to_dlq(redis, message_id, fields, str(error))
        await redis.xack(settings.stream_name, settings.consumer_group, message_id)
        await clear_retry_state(redis, message_id)
        return True
    except TRANSIENT_ERRORS:
        await recorder.record_failure(redis)
        attempts = await record_failure(redis, message_id)
        if attempts >= settings.max_retry_attempts:
            await move_to_dlq(redis, message_id, fields, "max_retry_attempts_exceeded")
            await redis.xack(settings.stream_name, settings.consumer_group, message_id)
            await clear_retry_state(redis, message_id)
        return True
    except Exception as error:
        await move_to_dlq(redis, message_id, fields, f"unexpected_error: {error}")
        await redis.xack(settings.stream_name, settings.consumer_group, message_id)
        await clear_retry_state(redis, message_id)
        return True


async def ensure_group(redis: Redis) -> None:
    try:
        await redis.xgroup_create(settings.stream_name, settings.consumer_group, id="0", mkstream=True)
    except ResponseError as error:
        if "BUSYGROUP" not in str(error):
            raise


async def read_pending(redis: Redis, consumer: str, count: int = 10):
    return await redis.xreadgroup(settings.consumer_group, consumer, {settings.stream_name: "0"}, count=count)


async def claim_abandoned(redis: Redis, consumer: str, count: int = 10):
    _, messages, _ = await redis.xautoclaim(
        settings.stream_name,
        settings.consumer_group,
        consumer,
        min_idle_time=5000,
        start_id="0-0",
        count=count,
    )
    return messages


async def read_fresh(redis: Redis, consumer: str, count: int = 10, block_ms: int = 1000):
    return await redis.xreadgroup(
        settings.consumer_group, consumer, {settings.stream_name: ">"}, count=count, block=block_ms
    )


async def update_lag(redis: Redis) -> None:
    groups = await redis.xinfo_groups(settings.stream_name)
    pending = next((group["pending"] for group in groups if group["name"] == settings.consumer_group), 0)
    await recorder.set_queue_lag(redis, pending)
