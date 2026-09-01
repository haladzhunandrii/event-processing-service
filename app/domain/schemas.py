from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionEvent(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    user_id: str = Field(min_length=1, max_length=128)
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    timestamp: datetime

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class SummaryResponse(BaseModel):
    user_id: str
    total_usd: str
    transaction_count: int


class TransactionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    amount: str
    currency: str
    amount_usd: str
    timestamp: datetime


class PaginatedTransactions(BaseModel):
    items: list[TransactionItem]
    page: int
    page_size: int
    total: int
