from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain.exceptions import UnsupportedCurrency
from app.domain.models import ExchangeRate, Transaction
from app.domain.schemas import TransactionEvent


def convert_to_usd(session, amount: Decimal, currency: str) -> Decimal:
    if currency == "USD":
        return amount
    rate = session.scalar(select(ExchangeRate.usd_rate).where(ExchangeRate.currency == currency))
    if rate is None:
        raise UnsupportedCurrency(f"No USD rate configured for {currency}")
    return amount * rate


def store_event(session, event: TransactionEvent) -> bool:
    """Store one event. Returns False when its event id was already committed."""
    try:
        with session.begin():
            if session.get(Transaction, event.id) is not None:
                return False
            amount_usd = convert_to_usd(session, event.amount, event.currency)
            session.add(
                Transaction(
                    id=event.id,
                    user_id=event.user_id,
                    amount=event.amount,
                    currency=event.currency,
                    timestamp=event.timestamp,
                    amount_usd=amount_usd,
                )
            )
        return True
    except IntegrityError:
        session.rollback()
        return False
