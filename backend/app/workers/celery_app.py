from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "irp_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.generate_report": {"queue": "reports"},
        "app.workers.tasks.enrich_ioc": {"queue": "enrichment"},
        "app.workers.tasks.verify_file_hash": {"queue": "default"},
        "app.workers.tasks.auto_detect_iocs_from_entry": {"queue": "default"},
        "app.workers.tasks.send_notification": {"queue": "default"},
        "app.workers.tasks.sync_to_sharepoint": {"queue": "default"},
    },
    beat_schedule={
        # Check for expired debounce locks every 10 seconds → fire sync tasks
        "check-debounce-locks": {
            "task": "app.workers.tasks.process_expired_sync_locks",
            "schedule": 10.0,
        },
    },
)
