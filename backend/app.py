from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

from decimal import Decimal
from fastapi import Depends, File, FastAPI, HTTPException, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI, OpenAIError
from openai.types.chat import ChatCompletionToolParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Transaction
from .schemas import ALLOWED_CATEGORIES, TransactionCreate, TransactionResponse
from .settings import Settings

app = FastAPI(title="AI Finance API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
FRONTEND_PATH = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_PATH / "static"), name="static")
MAX_AUDIO_BYTES = 10 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp4",
}
TRANSACTION_TOOL: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": "register_transaction",
        "description": "Register exactly one financial transaction from the user's text.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "amount": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Positive transaction amount in the user's currency.",
                },
                "category": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 50,
                    "enum": sorted(ALLOWED_CATEGORIES),
                    "description": "Categoria exclusivamente em português.",
                },
                "title": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 120,
                    "description": "Nome curto do gasto em português.",
                },
            },
            "required": ["amount", "category"],
        },
    },
}


api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


def require_api_key(x_api_key: str | None = Depends(api_key_header)) -> None:
    if not Settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A API_KEY precisa ser configurada no ambiente.",
        )
    if x_api_key != Settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API ausente ou inválida.",
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    return FileResponse(FRONTEND_PATH / "index.html")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
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
    _: None = Depends(require_api_key),
) -> list[Transaction]:
    return (
        db.query(Transaction)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@app.get("/transactions/totals", tags=["transactions"])
def transaction_totals(
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
) -> dict[str, object]:
    rows = (
        db.query(Transaction.category, func.sum(Transaction.amount).label("total"))
        .group_by(Transaction.category)
        .order_by(Transaction.category)
        .all()
    )
    totals = [
        {"category": category, "total": Decimal(total).quantize(Decimal("0.01"))}
        for category, total in rows
    ]
    return {
        "total": sum((item["total"] for item in totals), Decimal("0.00")),
        "by_category": totals,
    }


@app.get(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
    tags=["transactions"],
)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
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
    _: None = Depends(require_api_key),
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
    _: None = Depends(require_api_key),
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
    status_code=status.HTTP_200_OK,
    tags=["transactions"],
)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
) -> dict[str, str]:
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
    return {"message": "Transação excluída com sucesso."}


async def _save_transaction(transaction_data: TransactionCreate) -> Transaction:
    def save() -> Transaction:
        with SessionLocal() as db:
            return create_transaction(transaction_data, db)

    return await run_in_threadpool(save)


@app.post("/api/voice-transaction", response_model=TransactionResponse, tags=["voice"], status_code=status.HTTP_201_CREATED)
async def create_voice_transaction(
    file: UploadFile = File(...),
    _: None = Depends(require_api_key),
) -> Transaction:
    if not Settings.GROQ_API_KEY or not Settings.OPENROUTER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice transaction service is not configured.",
        )
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported audio type. Use WebM, WAV, or MP3.",
        )

    audio_bytes = await file.read(MAX_AUDIO_BYTES + 1)
    await file.close()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file must be 10 MB or smaller.",
        )
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The audio file is empty.",
        )

    extension = {
        "audio/webm": ".webm",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".mp4",
        "audio/wav": ".wav",
        "audio/wave": ".wav",
        "audio/x-wav": ".wav",
    }.get(content_type, ".wav")
    filename = f"{uuid4().hex}{extension}"
    transcription_client = AsyncOpenAI(
        api_key=Settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    extraction_client = AsyncOpenAI(
        api_key=Settings.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )

    try:
        transcription = await transcription_client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=(filename, audio_bytes, content_type),
            response_format="text",
        )
        transcript = str(transcription).strip()
        if not transcript:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No speech was detected in the audio.",
            )

        completion = await extraction_client.chat.completions.create(
            model=Settings.OPENROUTER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um categorizador financeiro brasileiro. "
                        "Extraia exatamente uma transação e chame register_transaction uma vez. "
                        "Responda SOMENTE com categorias em português, escolhendo uma das opções "
                        f"{', '.join(sorted(ALLOWED_CATEGORIES))}. "
                        "É proibido usar termos em inglês como food, gaming, transport ou bills. "
                        "Nunca invente valores ausentes; o valor deve ser positivo."
                    ),
                },
                {"role": "user", "content": transcript},
            ],
            tools=[TRANSACTION_TOOL],
            tool_choice={
                "type": "function",
                "function": {"name": "register_transaction"},
            },
            temperature=0,
        )
        tool_calls = completion.choices[0].message.tool_calls or []
        register_call = next(
            (
                tool_call
                for tool_call in tool_calls
                if tool_call.type == "function"
                and tool_call.function.name == "register_transaction"
            ),
            None,
        )
        if register_call is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The transaction could not be extracted from the audio.",
            )

        try:
            transaction_data = TransactionCreate.model_validate_json(
                register_call.function.arguments
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The extracted transaction data is invalid.",
            ) from exc

        return await _save_transaction(transaction_data)
    except OpenAIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The transcription or extraction service is unavailable.",
        ) from exc
    finally:
        await transcription_client.close()
        await extraction_client.close()
