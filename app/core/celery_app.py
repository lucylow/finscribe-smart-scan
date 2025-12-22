"""Celery application configuration."""
import os
from celery import Celery

# Redis broker URL
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "finscribe",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.core.tasks", "app.core.etl.pipeline"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={
        "app.core.tasks.ingest_task": {"queue": "cpu"},
        "app.core.tasks.preprocess_task": {"queue": "cpu"},
        "app.core.tasks.ocr_task": {"queue": "gpu"},  # OCR may use GPU
        "app.core.tasks.vlm_parse_task": {"queue": "gpu"},  # VLM uses GPU
        "app.core.tasks.postprocess_task": {"queue": "cpu"},
        "app.core.tasks.validate_task": {"queue": "cpu"},
        "app.core.tasks.index_task": {"queue": "cpu"},
    },
    task_default_queue="cpu",
    task_default_exchange="tasks",
    task_default_routing_key="default",
)


