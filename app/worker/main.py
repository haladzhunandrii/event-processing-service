import asyncio
import socket
from uuid import uuid4

from app.infrastructure.database import initialize_database
from app.infrastructure.queue import consumer
from app.infrastructure.redis import create_async_redis


async def run() -> None:
    initialize_database()
    consumer_name = f"{socket.gethostname()}-{uuid4().hex[:8]}"
    redis = create_async_redis()
    await consumer.ensure_group(redis)
    try:
        while True:
            handled_pending = False
            pending = await consumer.read_pending(redis, consumer_name)
            for _, messages in pending:
                for message_id, fields in messages:
                    if await consumer.handle_message(redis, message_id, fields):
                        handled_pending = True

            for message_id, fields in await consumer.claim_abandoned(redis, consumer_name):
                if await consumer.handle_message(redis, message_id, fields):
                    handled_pending = True

            if not handled_pending:
                fresh = await consumer.read_fresh(redis, consumer_name)
                for _, messages in fresh:
                    for message_id, fields in messages:
                        await consumer.handle_message(redis, message_id, fields)

            await consumer.update_lag(redis)
    finally:
        await redis.aclose()
