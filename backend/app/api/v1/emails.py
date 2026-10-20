import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.email_event import (
    EmailIngestRequest,
    EmailWebhookPayload,
    EmailLinkApplicationRequest,
    EmailEventResponse,
    EmailEventListResponse,
    EmailIngestTaskResponse
)
from app.workers.tasks import process_incoming_email_task
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emails", tags=["Emails & Communications"])

@router.post("/ingest", response_model=EmailIngestTaskResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_email(
    payload: EmailIngestRequest,
    db: Session = Depends(get_db)
):
    """
    Ingests an incoming recruitment email event.
    Dispatches asynchronous Celery worker task through Redis to categorize
    email, extract meeting links/deadlines, and link to candidate's pipeline.
    Falls back gracefully to synchronous execution if Celery broker is offline.
    """
    task_id = None
    email_event_id = None
    detected_cat = None
    linked_app_id = None

    try:
        # Dispatch to Celery background task
        async_result = process_incoming_email_task.delay(payload.model_dump())
        task_id = async_result.id
        status_msg = "Dispatched to background Celery worker"
    except Exception as exc:
        logger.warning(f"Celery broker dispatch offline ({exc}). Executing inline synchronously.")
        # Synchronous fallback so feature functions even in single-process test/dev mode
        event = EmailService.ingest_email_event(db=db, payload=payload)
        email_event_id = event.id
        detected_cat = event.detected_category.value
        linked_app_id = event.application_id
        status_msg = "Processed synchronously"

    return EmailIngestTaskResponse(
        status="queued" if task_id else "completed_inline",
        task_id=task_id,
        message_id=payload.message_id,
        details=status_msg,
        email_event_id=email_event_id,
        detected_category=detected_cat,
        linked_application_id=linked_app_id
    )

@router.post("/webhook", response_model=EmailIngestTaskResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_email_webhook(
    payload: EmailWebhookPayload,
    db: Session = Depends(get_db)
):
    """
    Webhook alias for inbound recruitment email event ingestion.
    Preserves backwards compatibility with existing webhook tests and integrations.
    """
    return ingest_email(payload=payload, db=db)

@router.get("", response_model=EmailEventListResponse)
def list_candidate_emails(
    category: Optional[str] = Query(None, description="Filter by detected category (e.g. INTERVIEWS, ASSESSMENTS, CONFIRMATIONS, REJECTIONS, SCAM)"),
    requires_review: Optional[bool] = Query(None, description="Filter by manual review flag"),
    application_id: Optional[int] = Query(None, description="Filter by linked application ID"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves candidate's categorized recruitment emails with linked application details.
    """
    items, total = EmailService.get_user_emails(
        db=db,
        user_id=current_user.id,
        category=category,
        requires_review=requires_review,
        application_id=application_id,
        skip=skip,
        limit=limit
    )

    return EmailEventListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )

@router.post("/{email_id}/link-application", response_model=EmailEventResponse)
def link_email_to_application(
    email_id: int,
    link_in: EmailLinkApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually connects an email event to an active candidate job application,
    updating the application's timeline and advancing its pipeline stage.
    """
    try:
        updated_event = EmailService.link_email_to_application(
            db=db,
            user_id=current_user.id,
            email_id=email_id,
            application_id=link_in.application_id
        )
        return updated_event
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
