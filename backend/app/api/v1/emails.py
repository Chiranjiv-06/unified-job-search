import logging
import secrets
from typing import Optional, Tuple
from fastapi import APIRouter, Depends, Query, status, HTTPException, Request, Header
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user, get_current_user_optional
from app.core.config import settings
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


def authenticate_email_ingestion(
    request: Request,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> Tuple[Optional[User], bool]:
    """
    Authenticates incoming email ingestion via either:
    1. Authenticated candidate session (Bearer token or cookie)
    2. Secure X-Webhook-Secret header for verified webhook integrations
    Returns (user, is_webhook). Raises 401 if unauthenticated.
    """
    if current_user:
        return current_user, False

    if x_webhook_secret and settings.WEBHOOK_SECRET:
        if secrets.compare_digest(x_webhook_secret, settings.WEBHOOK_SECRET):
            return None, True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please provide valid session credentials or an authorized X-Webhook-Secret header.",
        headers={"WWW-Authenticate": "Bearer"}
    )


@router.post("/ingest", response_model=EmailIngestTaskResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_email(
    payload: EmailIngestRequest,
    auth_ctx: Tuple[Optional[User], bool] = Depends(authenticate_email_ingestion),
    db: Session = Depends(get_db)
):
    """
    Ingests an incoming recruitment email event.
    Dispatches asynchronous Celery worker task through Redis to categorize
    email, extract meeting links/deadlines, and link to candidate's pipeline.
    Falls back gracefully to synchronous execution if Celery broker is offline.
    """
    user, is_webhook = auth_ctx
    if user:
        # Enforce candidate isolation: user cannot inject into another candidate's account
        payload.user_id = user.id
    else:
        # Webhook caller: require explicit and valid candidate user_id
        if not payload.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook payload must specify a valid target candidate user_id."
            )
        target_user = db.execute(select(User).where(User.id == payload.user_id)).scalar_one_or_none()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target candidate user ID {payload.user_id} was not found."
            )

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
    auth_ctx: Tuple[Optional[User], bool] = Depends(authenticate_email_ingestion),
    db: Session = Depends(get_db)
):
    """
    Webhook alias for inbound recruitment email event ingestion.
    Preserves backwards compatibility with existing webhook tests and integrations.
    """
    return ingest_email(payload=payload, auth_ctx=auth_ctx, db=db)

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
