"""FastAPI main application."""
import hmac
import hashlib
import logging
import json
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Header, Query
from fastapi.responses import JSONResponse

from app.config import settings, get_db_path
from app.models import (
    WebhookPayload,
    WebhookResponse,
    MessagesResponse,
    MessageItem,
    StatsResponse,
    SenderStats
)
from app.storage import Storage
from app.logging_utils import setup_logging, RequestLoggingMiddleware

# Setup logging
setup_logging(settings.log_level)
logger = logging.getLogger("app")

# Initialize storage
db_path = get_db_path(settings.database_url)
storage = Storage(db_path)

# Create FastAPI app
app = FastAPI(
    title="Webhook API",
    description="FastAPI backend for webhook message processing",
    version="1.0.0"
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature."""
    expected_signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)


@app.post("/webhook", response_model=WebhookResponse)
async def webhook(
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature")
):
    """
    Process webhook POST request.
    
    - Validates HMAC-SHA256 signature
    - Validates payload structure
    - Stores message idempotently
    """
    request_id = getattr(request.state, "request_id", None)
    
    # Get raw body for signature verification (must read before parsing)
    body = await request.body()
    
    # Verify signature
    if not x_signature:
        logger.warning(
            "Missing X-Signature header",
            extra={"request_id": request_id}
        )
        raise HTTPException(status_code=401, detail="Missing signature")
    
    if not verify_signature(body, x_signature, settings.webhook_secret):
        logger.warning(
            "Invalid signature",
            extra={"request_id": request_id}
        )
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse JSON payload
    try:
        payload_data = json.loads(body.decode())
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid JSON")
    
    # Validate payload
    try:
        payload = WebhookPayload(**payload_data)
    except Exception as e:
        raise HTTPException(status_code=422, detail="Invalid payload")
    
    # Store message (idempotent)
    inserted = storage.insert_message(
        message_id=payload.message_id,
        from_number=payload.from_number,
        to_number=payload.to_number,
        ts=payload.ts,
        text=payload.text
    )
    
    # Log webhook-specific fields
    logger.info(
        "Webhook processed",
        extra={
            "request_id": request_id,
            "message_id": payload.message_id,
            "dup": not inserted,
            "result": "ok"
        }
    )
    
    return WebhookResponse(status="ok")


@app.get("/messages", response_model=MessagesResponse)
async def get_messages(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    from_number: Optional[str] = Query(None, alias="from"),
    since: Optional[str] = Query(None),
    q: Optional[str] = Query(None)
):
    """
    Get messages with filtering and pagination.
    
    Query parameters:
    - limit: Number of messages to return (1-100, default 50)
    - offset: Number of messages to skip (default 0)
    - from: Filter by sender phone number
    - since: Filter by timestamp (ISO-8601)
    - q: Search in message text
    """
    messages, total = storage.get_messages(
        limit=limit,
        offset=offset,
        from_number=from_number,
        since=since,
        q=q
    )
    
    return MessagesResponse(
        items=[MessageItem(**msg) for msg in messages],
        total=total,
        limit=limit,
        offset=offset
    )


@app.get("/stats", response_model=StatsResponse)
async def get_stats(request: Request):
    """Get statistics about messages."""
    stats = storage.get_stats()
    
    return StatsResponse(
        total_messages=stats["total_messages"],
        senders_count=stats["senders_count"],
        messages_per_sender=[
            SenderStats(**sender) for sender in stats["messages_per_sender"]
        ],
        first_message_ts=stats["first_message_ts"],
        last_message_ts=stats["last_message_ts"]
    )


@app.get("/health/live")
async def health_live():
    """Liveness probe - always returns 200."""
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    """Readiness probe - checks WEBHOOK_SECRET and database."""
    # Check WEBHOOK_SECRET
    if not settings.webhook_secret:
        raise HTTPException(status_code=503, detail="WEBHOOK_SECRET not configured")
    
    # Check database
    if not storage.health_check():
        raise HTTPException(status_code=503, detail="Database not reachable")
    
    return {"status": "ok"}


@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    """Handle validation errors."""
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid payload"}
    )
