from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.exceptions import UnsupportedCurrency
from app.domain.models import Base, ExchangeRate
from app.services.processor import convert_to_usd


def _session_with_rates(currencies: dict[str, str]):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory.begin() as session:
        for currency, rate in currencies.items():
            session.add(ExchangeRate(currency=currency, usd_rate=Decimal(rate)))
    return factory


def test_convert_eur_to_usd():
    factory = _session_with_rates({"EUR": "1.08"})
    with factory() as session:
        assert convert_to_usd(session, Decimal("10"), "EUR") == Decimal("10.80")


def test_convert_usd_passthrough():
    factory = _session_with_rates({"USD": "1"})
    with factory() as session:
        assert convert_to_usd(session, Decimal("25"), "USD") == Decimal("25")


def test_convert_unsupported_raises():
    factory = _session_with_rates({"EUR": "1.08"})
    with factory() as session:
        with pytest.raises(UnsupportedCurrency):
            convert_to_usd(session, Decimal("10"), "XXX")
