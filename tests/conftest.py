import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain.models import Base, ExchangeRate
from app.domain.schemas import TransactionEvent


@pytest.fixture
def event_factory():
    def _factory(id="evt-1", amount="10", currency="EUR", user_id="user-1"):
        return TransactionEvent(
            id=id,
            user_id=user_id,
            amount=Decimal(amount),
            currency=currency,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )

    return _factory


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory.begin() as session:
        session.add(ExchangeRate(currency="USD", usd_rate=Decimal("1")))
        session.add(ExchangeRate(currency="EUR", usd_rate=Decimal("1.08")))
    with factory() as session:
        yield session
