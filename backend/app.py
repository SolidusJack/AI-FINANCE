from collections.abc import Generator

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Transaction
from .schemas import TransactionCreate, TransactionResponse

app = FastAPI(title="AI Finance API")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", tags=["health"])
def read_root() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/transactions",
    response_model=list[TransactionResponse],
    tags=["transactions"],
)
def list_transactions(
    skip: int = Query(default=0, ge=0, le=100_000),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Transaction]:
    return (
        db.query(Transaction)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@app.get(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
    tags=["transactions"],
)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
) -> Transaction:
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return transaction


@app.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["transactions"],
)
def create_transaction(
    transaction_data: TransactionCreate,
    db: Session = Depends(get_db),
) -> Transaction:
    transaction = Transaction(**transaction_data.model_dump())
    db.add(transaction)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction could not be created",
        ) from exc
    db.refresh(transaction)
    return transaction


@app.put(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
    tags=["transactions"],
)
def update_transaction(
    transaction_id: int,
    transaction_data: TransactionCreate,
    db: Session = Depends(get_db),
) -> Transaction:
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    for field, value in transaction_data.model_dump().items():
        setattr(transaction, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction could not be updated",
        ) from exc
    db.refresh(transaction)
    return transaction


@app.delete(
    "/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["transactions"],
)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
) -> None:
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    db.delete(transaction)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transaction could not be deleted",
        ) from exc
