from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from openai import AsyncOpenAI, OpenAIError
from openai.types.chat import ChatCompletionToolParam
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Transaction
from .schemas import TransactionCreate, TransactionResponse
from .settings import Settings

app = FastAPI(title="AI Finance API")
FRONTEND_PATH = Path(__file__).resolve().parent.parent / "index.html"
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
                    "description": "Short category such as Food, Transport, or Bills.",
                },
            },
            "required": ["amount", "category"],
        },
    },
}


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    return FileResponse(FRONTEND_PATH)


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


async def _save_transaction(transaction_data: TransactionCreate) -> Transaction:
    def save() -> Transaction:
        with SessionLocal() as db:
            return create_transaction(transaction_data, db)

    return await run_in_threadpool(save)


@app.post("/api/voice-transaction", response_model=TransactionResponse, tags=["voice"], status_code=status.HTTP_201_CREATED)
async def create_voice_transaction(
    audio: UploadFile = File(...),
) -> Transaction:
    if not Settings.GROQ_API_KEY or not Settings.OPENROUTER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice transaction service is not configured.",
        )
    if audio.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported audio type. Use WebM, WAV, or MP3.",
        )

    audio_bytes = await audio.read(MAX_AUDIO_BYTES + 1)
    await audio.close()
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
    }.get(audio.content_type or "", ".wav")
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
            file=(filename, audio_bytes, audio.content_type),
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
                        "Extract one transaction from the transcript. "
                        "Call register_transaction exactly once. Never invent missing values. "
                        "The amount must be positive and category must be short."
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
