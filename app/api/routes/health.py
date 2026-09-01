from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.infrastructure.database import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request):
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        await request.app.state.redis.ping()
    except Exception as error:
        return JSONResponse(status_code=503, content={"status": "not_ready", "detail": str(error)})
    return {"status": "ready"}
