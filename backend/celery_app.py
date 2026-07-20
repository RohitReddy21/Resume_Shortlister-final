import os

from celery import Celery
from app.core.config import get_settings

settings = get_settings()
broker = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
backend = os.getenv("CELERY_RESULT_BACKEND", broker)

celery = Celery(
    "resumeparser",
    broker=broker,
    backend=backend,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery.autodiscover_tasks(["app.services.parser", "app.services.anonymizer_tasks"])
