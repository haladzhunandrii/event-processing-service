from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from decimal import Decimal

from .config import DATABASE_URL
from .models import Base, ExchangeRate

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def initialize_database() -> None:
    Base.metadata.create_all(engine)
    # Deliberately small local rate table; production would update this from a rate provider.
    with SessionLocal.begin() as session:
        for currency, value in {"USD": "1", "EUR": "1.08", "UAH": "0.024"}.items():
            if session.get(ExchangeRate, currency) is None:
                session.add(ExchangeRate(currency=currency, usd_rate=Decimal(value)))
