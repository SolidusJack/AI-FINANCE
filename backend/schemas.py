from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TransactionBase(BaseModel):
    amount: Decimal = Field(
        ...,
        gt=0,
        le=99_999_999.99,
        description="The amount of the transaction, must be greater than 0",
    )
    category: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="The category of the transaction",
    )

class TransactionCreate(TransactionBase):
    date: datetime = Field(
        default_factory=datetime.now,
        description="The date of the transaction",
    )

class TransactionResponse(TransactionBase):
    id: int
    date: datetime

    model_config = {"from_attributes": True}