from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "job_search_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes maximum runtime
    worker_prefetch_multiplier=1,
)

# Optional broker connection retry on startup
celery_app.conf.broker_connection_retry_on_startup = True
