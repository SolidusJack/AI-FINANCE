from pydantic import BaseModel,Field
from decimal import Decimal
from datetime import datetime

class TransactionBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    category: str = Field(..., max_length=50)

class TransactionCreate(TransactionBase):
    date: datetime = Field(default_factory=datetime.now)

class TransactionResponse(TransactionBase):
    id: int
    date: datetime 
    
    model_config = {"from_attributes": True}