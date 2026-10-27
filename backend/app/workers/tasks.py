import logging
from typing import Dict, Any, Optional
from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.schemas.email_event import EmailIngestRequest, EmailWebhookPayload
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

@celery_app.task(name="process_incoming_email_task", bind=True, max_retries=3, default_retry_delay=60)
def process_incoming_email_task(self, email_data: Dict[str, Any], db_session=None) -> Dict[str, Any]:
    """
    Celery background worker task:
    1. Validates incoming email webhook payload.
    2. Inspects sender domain, subject, and body.
    3. Resolves and links to matching Application via company domain or name.
    4. Categorizes the event (Interview, Assessment, Confirmation, Rejection, Scam Alert).
    5. Persists the EmailEvent and updates application lifecycle stage.
    """
    db = db_session or SessionLocal()
    close_on_finish = db_session is None
    try:
        logger.info(f"Processing incoming email message_id={email_data.get('message_id')}")
        payload = EmailIngestRequest.model_validate(email_data)
        
        email_event = EmailService.ingest_email_event(db=db, payload=payload)
        
        result = {
            "status": "success",
            "email_event_id": email_event.id,
            "message_id": email_event.message_id,
            "linked_application_id": email_event.application_id,
            "detected_category": email_event.detected_category.value,
            "parsed_details": email_event.parsed_details or {}
        }
        logger.info(f"Successfully processed email event: {result}")
        return result

    except Exception as exc:
        logger.error(f"Error processing email event: {exc}", exc_info=True)
        # Retry with exponential backoff on transient errors if run by celery
        if hasattr(self, "retry"):
            try:
                raise self.retry(exc=exc)
            except Exception:
                raise exc
        raise exc
    finally:
        if close_on_finish:
            db.close()
@celery_app.task(name="orchestrate_job_ingestion_task", bind=True, max_retries=2, default_retry_delay=120)
def orchestrate_job_ingestion_task(
    self,
    sources: Optional[list] = None,
    limit_per_source: int = 20,
    db_session=None
) -> Dict[str, Any]:
    """
    Celery background worker task:
    1. Fetches listings from enabled external sources (RemoteOK, Jobicy).
    2. Runs multi-tier deduplication.
    3. Safely upserts records and marks stale jobs as expired.
    4. Records execution telemetry.
    """
    from app.services.job_ingestion_service import JobIngestionService
    db = db_session or SessionLocal()
    close_on_finish = db_session is None
    try:
        logger.info(f"Starting job ingestion background task for sources={sources}, limit={limit_per_source}")
        result = JobIngestionService.sync_sources(
            db=db,
            sources=sources,
            limit_per_source=limit_per_source
        )
        logger.info(f"Completed job ingestion background task: {result}")
        return result
    except Exception as exc:
        logger.error(f"Error in job ingestion background task: {exc}", exc_info=True)
        if hasattr(self, "retry"):
            try:
                raise self.retry(exc=exc)
            except Exception:
                raise exc
        raise exc
    finally:
        if close_on_finish:
            db.close()
