from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.core.enums import EmailCategory

class EmailWebhookPayload(BaseModel):
    message_id: str = Field(..., min_length=1, max_length=255, description="Unique message ID from email provider (e.g. Gmail)")
    sender_email: EmailStr = Field(..., description="From email address")
    subject: str = Field(..., min_length=1, max_length=500, description="Email subject line")
    body_text: str = Field(..., description="Plaintext or sanitized body content")
    user_id: int = Field(..., description="Target candidate/user ID")
    received_at: Optional[datetime] = None

class EmailEventResponse(BaseModel):
    id: int
    application_id: Optional[int] = None
    user_id: int
    message_id: str
    sender_email: str
    subject: str
    detected_category: EmailCategory
    parsed_details: Dict[str, Any] = {}
    received_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EmailIngestTaskResponse(BaseModel):
    status: str = "queued"
    task_id: Optional[str] = None
    message_id: str
    details: str
