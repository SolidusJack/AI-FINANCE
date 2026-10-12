from datetime import datetime
from decimal import Decimal
from sqlalchemy import Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column

class Base(MappedAsDataclass, DeclarativeBase):
    pass

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    category: Mapped[str] = mapped_column(String(50))
    date: Mapped[datetime]
