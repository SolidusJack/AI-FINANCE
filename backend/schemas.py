from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

ALLOWED_CATEGORIES = {
    "Alimentação",
    "Transporte",
    "Moradia",
    "Saúde",
    "Educação",
    "Lazer",
    "Jogos",
    "Contas",
    "Compras",
    "Serviços",
    "Outros",
}


class TransactionBase(BaseModel):
    title: str = Field(
        default="Compra",
        min_length=1,
        max_length=120,
        strip_whitespace=True,
    )
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

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        normalized = " ".join(value.split()).strip()
        if normalized not in ALLOWED_CATEGORIES:
            raise ValueError("Escolha uma categoria válida em português.")
        return normalized

class TransactionCreate(TransactionBase):
    date: datetime = Field(
        default_factory=datetime.now,
        description="The date of the transaction",
    )

class TransactionResponse(TransactionBase):
    id: int
    date: datetime

    model_config = {"from_attributes": True}