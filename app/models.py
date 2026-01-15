"""Data models for webhook payloads and responses."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class WebhookPayload(BaseModel):
    """Webhook payload model with validation."""
    message_id: str = Field(..., min_length=1)
    from_number: str = Field(..., alias="from")
    to_number: str = Field(..., alias="to")
    ts: str
    text: Optional[str] = Field(None, max_length=4096)
    
    @field_validator("from_number", "to_number")
    @classmethod
    def validate_e164(cls, v: str) -> str:
        """Validate E.164 format (+digits)."""
        if not re.match(r"^\+\d+$", v):
            raise ValueError("Must be in E.164 format (+digits)")
        return v
    
    @field_validator("ts")
    @classmethod
    def validate_iso8601_utc(cls, v: str) -> str:
        """Validate ISO-8601 UTC timestamp with Z."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            if not v.endswith("Z"):
                raise ValueError("Timestamp must end with Z")
            return v
        except ValueError as e:
            raise ValueError("Invalid ISO-8601 UTC timestamp") from e


class WebhookResponse(BaseModel):
    """Webhook response model."""
    status: str = "ok"


class MessageItem(BaseModel):
    """Message item for GET /messages response."""
    message_id: str
    from_number: str = Field(alias="from")
    to_number: str = Field(alias="to")
    ts: str
    text: Optional[str] = None


class MessagesResponse(BaseModel):
    """GET /messages response model."""
    items: list[MessageItem]
    total: int
    limit: int
    offset: int


class SenderStats(BaseModel):
    """Sender statistics model."""
    from_number: str = Field(alias="from")
    count: int


class StatsResponse(BaseModel):
    """GET /stats response model."""
    total_messages: int
    senders_count: int
    messages_per_sender: list[SenderStats]
    first_message_ts: Optional[str] = None
    last_message_ts: Optional[str] = None
