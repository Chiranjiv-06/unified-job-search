import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.email_event import EmailWebhookPayload, EmailIngestTaskResponse
from app.workers.tasks import process_incoming_email_task
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emails", tags=["Emails & Webhooks"])

@router.post("/webhook", response_model=EmailIngestTaskResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_email_webhook(
    payload: EmailWebhookPayload,
    db: Session = Depends(get_db)
):
    """
    Ingests an incoming recruitment email event via webhook.
    Dispatches asynchronous Celery worker task to classify email,
    resolve employer, and link to candidate application.
    Falls back gracefully to synchronous execution if Redis/Celery broker is unavailable.
    """
    task_id = None
    try:
        # Dispatch to Celery background task
        async_result = process_incoming_email_task.delay(payload.model_dump())
        task_id = async_result.id
        status_msg = "Dispatched to background Celery worker"
    except Exception as exc:
        logger.warning(f"Celery dispatch failed or broker offline ({exc}). Executing inline synchronously.")
        # Synchronous fallback so feature functions even in single-process test/dev mode
        EmailService.ingest_email_event(db=db, payload=payload)
        status_msg = "Processed synchronously"

    return EmailIngestTaskResponse(
        status="queued" if task_id else "completed_inline",
        task_id=task_id,
        message_id=payload.message_id,
        details=status_msg
    )
