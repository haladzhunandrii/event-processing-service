from collections.abc import Generator

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def get_redis(request: Request) -> Redis:
    return request.app.state.redis
