import json
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from prometheus_client import make_asgi_app
from redis.asyncio import Redis
from sqlalchemy import func, select

from .config import REDIS_URL, STREAM
from .db import SessionLocal, initialize_database
from .models import Transaction
from .schemas import TransactionEvent


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    app.state.redis = Redis.from_url(REDIS_URL, decode_responses=True)
    yield
    await app.state.redis.aclose()


app = FastAPI(title="Transaction Event Service", lifespan=lifespan)
app.mount("/metrics", make_asgi_app())


@app.post("/events", status_code=202)
async def receive_event(event: TransactionEvent):
    message_id = await app.state.redis.xadd(STREAM, {"event": event.model_dump_json()})
    return {"status": "queued", "message_id": message_id, "event_id": event.id}


@app.get("/users/{user_id}/summary")
def summary(user_id: str):
    with SessionLocal() as session:
        total, count = session.execute(select(func.coalesce(func.sum(Transaction.amount_usd), 0), func.count()).where(Transaction.user_id == user_id)).one()
    return {"user_id": user_id, "total_usd": str(total), "transaction_count": count}


@app.get("/users/{user_id}/transactions")
def transactions(user_id: str, from_: datetime = Query(alias="from"), to: datetime = Query(), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100)):
    with SessionLocal() as session:
        filters = (Transaction.user_id == user_id, Transaction.timestamp >= from_, Transaction.timestamp <= to)
        total = session.scalar(select(func.count()).select_from(Transaction).where(*filters))
        rows = session.scalars(select(Transaction).where(*filters).order_by(Transaction.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [{"id": x.id, "amount": str(x.amount), "currency": x.currency, "amount_usd": str(x.amount_usd), "timestamp": x.timestamp} for x in rows], "page": page, "page_size": page_size, "total": total}
