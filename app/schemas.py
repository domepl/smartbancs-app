from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class TransactionCreate(BaseModel):
    source_account: str = Field(
        min_length=1,
        max_length=30,
    )

    destination_account: str = Field(
        min_length=1,
        max_length=30,
    )

    amount: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=2,
    )

    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
    )

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str):
        return value.upper()


class TransactionResponse(BaseModel):
    transaction_id: str
    source_account: str
    destination_account: str
    amount: Decimal
    currency: str
    status: str
    created_at: datetime