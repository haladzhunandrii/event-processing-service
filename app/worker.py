import asyncio
import json
import socket
import time
from uuid import uuid4

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from .config import GROUP, REDIS_URL, STREAM
from .db import SessionLocal, initialize_database
from .metrics import EVENT_FAILURES, EVENTS_PROCESSED, QUEUE_LAG
from .processor import store_event
from .schemas import TransactionEvent

RETRY_PREFIX = "retry:"
MAX_BACKOFF_SECONDS = 60


async def ensure_group(redis: Redis) -> None:
    try:
        await redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except ResponseError as error:
        if "BUSYGROUP" not in str(error):
            raise


async def should_attempt(redis: Redis, message_id: str) -> bool:
    return time.time() >= float(await redis.hget(RETRY_PREFIX + message_id, "next_at") or 0)


async def record_failure(redis: Redis, message_id: str) -> None:
    key = RETRY_PREFIX + message_id
    attempts = await redis.hincrby(key, "attempts", 1)
    delay = min(2 ** min(attempts, 6), MAX_BACKOFF_SECONDS)
    await redis.hset(key, mapping={"next_at": time.time() + delay})
    await redis.expire(key, 86400)


async def process(redis: Redis, consumer: str, message_id: str, fields: dict) -> bool:
    if not await should_attempt(redis, message_id):
        return False
    try:
        event = TransactionEvent.model_validate_json(fields["event"])
        with SessionLocal() as session:
            inserted = store_event(session, event)
        # Ack happens after the commit. A crash before this point causes safe redelivery.
        await redis.xack(STREAM, GROUP, message_id)
        await redis.delete(RETRY_PREFIX + message_id)
        if inserted:
            EVENTS_PROCESSED.inc()
        return True
    except Exception:
        EVENT_FAILURES.inc()
        await record_failure(redis, message_id)
        return False


async def update_lag(redis: Redis) -> None:
    groups = await redis.xinfo_groups(STREAM)
    pending = next((group["pending"] for group in groups if group["name"] == GROUP), 0)
    QUEUE_LAG.set(pending)


async def run() -> None:
    initialize_database()
    consumer = f"{socket.gethostname()}-{uuid4().hex[:8]}"
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    await ensure_group(redis)
    try:
        while True:
            # First revisit this consumer's unacknowledged messages, honoring their retry time.
            pending = await redis.xreadgroup(GROUP, consumer, {STREAM: "0"}, count=10)
            handled_pending = False
            for _, messages in pending:
                for message_id, fields in messages:
                    handled_pending = await process(redis, consumer, message_id, fields) or handled_pending
            # If this is a replacement worker, take messages abandoned by a dead consumer.
            # Redis retains the message until this code successfully acknowledges it.
            _, abandoned, _ = await redis.xautoclaim(
                STREAM, GROUP, consumer, min_idle_time=5000, start_id="0-0", count=10
            )
            for message_id, fields in abandoned:
                handled_pending = await process(redis, consumer, message_id, fields) or handled_pending
            if not handled_pending:
                fresh = await redis.xreadgroup(GROUP, consumer, {STREAM: ">"}, count=10, block=1000)
                for _, messages in fresh:
                    for message_id, fields in messages:
                        await process(redis, consumer, message_id, fields)
            await update_lag(redis)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run())
