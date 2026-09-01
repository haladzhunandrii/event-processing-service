from datetime import datetime

from sqlalchemy import func, select

from app.domain.models import Transaction
from app.domain.schemas import PaginatedTransactions, SummaryResponse, TransactionItem


def get_user_summary(session, user_id: str) -> SummaryResponse:
    total, count = session.execute(
        select(func.coalesce(func.sum(Transaction.amount_usd), 0), func.count()).where(
            Transaction.user_id == user_id
        )
    ).one()
    return SummaryResponse(user_id=user_id, total_usd=str(total), transaction_count=count)


def list_user_transactions(
    session,
    user_id: str,
    from_: datetime,
    to: datetime,
    page: int,
    page_size: int,
) -> PaginatedTransactions:
    filters = (
        Transaction.user_id == user_id,
        Transaction.timestamp >= from_,
        Transaction.timestamp <= to,
    )
    total = session.scalar(select(func.count()).select_from(Transaction).where(*filters))
    rows = session.scalars(
        select(Transaction)
        .where(*filters)
        .order_by(Transaction.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        TransactionItem(
            id=row.id,
            amount=str(row.amount),
            currency=row.currency,
            amount_usd=str(row.amount_usd),
            timestamp=row.timestamp,
        )
        for row in rows
    ]
    return PaginatedTransactions(items=items, page=page, page_size=page_size, total=total or 0)
