from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.services import queries

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/summary")
def summary(user_id: str, session: Session = Depends(get_db)):
    return queries.get_user_summary(session, user_id)


@router.get("/{user_id}/transactions")
def transactions(
    user_id: str,
    session: Session = Depends(get_db),
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    return queries.list_user_transactions(session, user_id, from_, to, page, page_size)
