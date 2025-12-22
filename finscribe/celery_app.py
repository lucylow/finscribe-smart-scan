"""
celery_app.py

Celery application factory / module. Configure broker via env var CELERY_BROKER_URL.
Example broker: redis://redis:6379/0
"""

import os
from celery import Celery

CELERY_BROKER = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
CELERY_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER)

celery_app = Celery("finscribe_tasks", broker=CELERY_BROKER, backend=CELERY_BACKEND)

# Basic recommended conf; tune in prod
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="ocr",
    timezone="UTC",
    enable_utc=True,
)

