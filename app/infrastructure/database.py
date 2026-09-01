from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.domain.models import Base, ExchangeRate

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

SEED_RATES = {"USD": "1", "EUR": "1.08", "UAH": "0.024"}


def initialize_database() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as session:
        for currency, value in SEED_RATES.items():
            if session.get(ExchangeRate, currency) is None:
                session.add(ExchangeRate(currency=currency, usd_rate=Decimal(value)))
