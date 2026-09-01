from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, ExchangeRate, Transaction
from app.processor import store_event
from app.schemas import TransactionEvent


def event(id="evt-1", amount="10", currency="EUR"):
    return TransactionEvent(id=id, user_id="user-1", amount=Decimal(amount), currency=currency, timestamp=datetime(2026, 1, 1, tzinfo=UTC))


def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory.begin() as session:
        session.add(ExchangeRate(currency="EUR", usd_rate=Decimal("1.08")))
    return factory


def test_converts_to_usd():
    factory = session_factory()
    with factory() as session:
        assert store_event(session, event()) is True
    with factory() as session:
        stored = session.get(Transaction, "evt-1")
        assert stored.amount_usd == Decimal("10.8000")


def test_duplicate_event_is_not_stored_twice():
    factory = session_factory()
    with factory() as session:
        assert store_event(session, event()) is True
    with factory() as session:
        assert store_event(session, event()) is False
        assert session.query(Transaction).count() == 1
