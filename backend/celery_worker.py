from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ticket_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.sla_tasks",
        "app.tasks.export_tasks",
        "app.tasks.email_tasks",
    ],
)

celery_app.conf.beat_schedule = {
    "scan-sla-deadlines": {
        "task": "tasks.scan_sla_deadlines",
        "schedule": 300.0,
    },
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
)
