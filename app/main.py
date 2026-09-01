from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CollectorRegistry, GCCollector, ProcessCollector, generate_latest

from app.api.routes import events, health, users
from app.infrastructure.database import initialize_database
from app.infrastructure.metrics.exposition import RedisMetricsCollector
from app.infrastructure.redis import create_async_redis, create_sync_redis

metrics_registry = CollectorRegistry()
sync_redis = create_sync_redis()
metrics_registry.register(RedisMetricsCollector(sync_redis))
GCCollector(registry=metrics_registry)
ProcessCollector(registry=metrics_registry)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    app.state.redis = create_async_redis()
    yield
    await app.state.redis.aclose()


def create_app() -> FastAPI:
    app = FastAPI(title="Transaction Event Service", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(events.router)
    app.include_router(users.router)

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(metrics_registry), media_type="text/plain; version=0.0.4; charset=utf-8")

    return app


app = create_app()
