from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from app.api.dependencies import get_redis
from app.domain.schemas import TransactionEvent
from app.services.publisher import enqueue_event

router = APIRouter()


@router.post("/events", status_code=202)
async def receive_event(event: TransactionEvent, redis: Redis = Depends(get_redis)):
    message_id = await enqueue_event(redis, event)
    return {"status": "queued", "message_id": message_id, "event_id": event.id}
