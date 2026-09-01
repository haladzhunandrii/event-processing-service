from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .models import ExchangeRate, Transaction
from .schemas import TransactionEvent


class UnsupportedCurrency(ValueError):
    pass


def store_event(session, event: TransactionEvent) -> bool:
    """Store one event. Returns False when its event id was already committed."""
    try:
        with session.begin():
            if session.get(Transaction, event.id) is not None:
                return False
            if event.currency == "USD":
                rate = Decimal("1")
            else:
                rate = session.scalar(select(ExchangeRate.usd_rate).where(ExchangeRate.currency == event.currency))
                if rate is None:
                    raise UnsupportedCurrency(f"No USD rate configured for {event.currency}")
            # The primary key is the idempotency barrier for concurrent consumers.
            session.add(Transaction(
                id=event.id, user_id=event.user_id, amount=event.amount,
                currency=event.currency, timestamp=event.timestamp,
                amount_usd=event.amount * rate,
            ))
        return True
    except IntegrityError:
        session.rollback()
        return False
