from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(120), default="Compra")
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    category: Mapped[str] = mapped_column(String(50))
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
