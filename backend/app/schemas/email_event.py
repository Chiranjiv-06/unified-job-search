import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.core.enums import EmailCategory

class EmailIngestRequest(BaseModel):
    message_id: Optional[str] = Field(None, max_length=255, description="Unique message ID from provider")
    sender: Optional[str] = Field(None, description="Sender name or email")
    sender_email: Optional[str] = Field(None, description="From email address")
    subject: str = Field(..., min_length=1, max_length=500, description="Email subject line")
    body: Optional[str] = Field(None, description="Email body content")
    body_text: Optional[str] = Field(None, description="Plaintext or sanitized body content")
    date: Optional[datetime] = None
    received_at: Optional[datetime] = None
    user_id: Optional[int] = Field(None, description="Target candidate/user ID")

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize sender / sender_email
            if not data.get("sender_email") and data.get("sender"):
                data["sender_email"] = data["sender"]
            elif not data.get("sender") and data.get("sender_email"):
                data["sender"] = data["sender_email"]

            if not data.get("sender_email"):
                data["sender_email"] = "unknown@domain.com"

            # Normalize body / body_text
            if not data.get("body_text") and data.get("body"):
                data["body_text"] = data["body"]
            elif not data.get("body") and data.get("body_text"):
                data["body"] = data["body_text"]

            if not data.get("body_text"):
                data["body_text"] = ""

            # Normalize received_at / date
            if not data.get("received_at") and data.get("date"):
                data["received_at"] = data["date"]
            elif not data.get("received_at"):
                data["received_at"] = datetime.now(timezone.utc)

            # Generate unique message_id if absent
            if not data.get("message_id"):
                data["message_id"] = f"msg_{uuid.uuid4().hex[:16]}"

        return data

# Backwards compatible alias
class EmailWebhookPayload(EmailIngestRequest):
    pass

class EmailLinkApplicationRequest(BaseModel):
    application_id: int = Field(..., description="Application ID to link this email event to")

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

    # Denormalized application summary fields for easy frontend display
    application_job_title: Optional[str] = None
    application_company_name: Optional[str] = None
    application_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class EmailEventListResponse(BaseModel):
    items: List[EmailEventResponse]
    total: int
    skip: int
    limit: int

class EmailIngestTaskResponse(BaseModel):
    status: str = "queued"
    task_id: Optional[str] = None
    message_id: str
    details: str
    email_event_id: Optional[int] = None
    detected_category: Optional[str] = None
    linked_application_id: Optional[int] = None
