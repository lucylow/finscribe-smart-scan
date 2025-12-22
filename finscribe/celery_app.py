# finscribe/celery_app.py
"""
Minimal Celery app factory and instance.

Place this file at finscribe/celery_app.py so other modules can import:
  from finscribe.celery_app import celery_app

The Celery configuration is read from environment variables:
 - CELERY_BROKER_URL (required)
 - CELERY_RESULT_BACKEND (optional)
"""

import os
from celery import Celery

BROKER = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", os.getenv("CELERY_BROKER_URL"))

celery_app = Celery(
    "finscribe",
    broker=BROKER,
    backend=RESULT_BACKEND,
)

# Basic recommended defaults; override via env if needed
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_proc_alive_timeout=300,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
)

# Optionally autodiscover tasks in package modules
# celery_app.autodiscover_tasks(['finscribe'])

if __name__ == "__main__":
    print("Celery app configured with broker:", BROKER)
