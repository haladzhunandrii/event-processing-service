from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.domain.exceptions import UnsupportedCurrency
from app.domain.models import Base, ExchangeRate, Transaction
from app.services.processor import convert_to_usd, store_event


def _session_with_rates(currencies: dict[str, str]):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory.begin() as session:
        for currency, rate in currencies.items():
            session.add(ExchangeRate(currency=currency, usd_rate=Decimal(rate)))
    return factory


def test_converts_to_usd(event_factory):
    factory = _session_with_rates({"EUR": "1.08"})
    with factory() as session:
        assert store_event(session, event_factory()) is True
    with factory() as session:
        stored = session.get(Transaction, "evt-1")
        assert stored.amount_usd == Decimal("10.8000")


def test_duplicate_event_is_not_stored_twice(event_factory):
    factory = _session_with_rates({"EUR": "1.08"})
    with factory() as session:
        assert store_event(session, event_factory()) is True
    with factory() as session:
        assert store_event(session, event_factory()) is False
        assert session.scalar(select(Transaction).where(Transaction.id == "evt-1")) is not None
        assert len(session.scalars(select(Transaction)).all()) == 1


def test_usd_shortcut(event_factory):
    factory = _session_with_rates({"USD": "1"})
    with factory() as session:
        assert store_event(session, event_factory(currency="USD")) is True
    with factory() as session:
        stored = session.get(Transaction, "evt-1")
        assert stored.amount_usd == Decimal("10")


def test_unsupported_currency(event_factory):
    factory = _session_with_rates({"EUR": "1.08"})
    with factory() as session:
        with pytest.raises(UnsupportedCurrency):
            store_event(session, event_factory(currency="XXX"))
