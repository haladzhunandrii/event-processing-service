import json
import time

from redis.asyncio import Redis

from app.config import settings


async def move_to_dlq(redis: Redis, message_id: str, fields: dict, reason: str) -> str:
    event_payload = fields.get("event", "")
    event_id = ""
    try:
        parsed = json.loads(event_payload)
        event_id = parsed.get("id", "")
    except (json.JSONDecodeError, TypeError):
        pass

    return await redis.xadd(
        settings.dlq_stream,
        {
            "original_message_id": message_id,
            "event_id": event_id,
            "reason": reason,
            "failed_at": str(time.time()),
            "event": event_payload,
        },
    )
