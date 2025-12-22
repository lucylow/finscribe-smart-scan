"""
tasks.py

Celery tasks that:
- read staged images
- call OCR client
- store per-page OCR JSON artifacts
- call a semantic parser stub (optional) or write raw OCR results to results artifact

This example uses LocalStorage by default; replace with MinIOStorage in production.
"""

import os
import json
import logging
from typing import Any, Optional
from .celery_app import celery_app
from .ocr_client import get_ocr_client
from .staging import LocalStorage, StorageInterface, read_bytes_from_storage, Boto3StorageAdapter
from datetime import datetime

logger = logging.getLogger(__name__)

# Storage instance - in real app inject via DI
STORAGE_BASE = os.getenv("STORAGE_BASE", "./storage")
_storage: Optional[StorageInterface] = None


def get_storage() -> StorageInterface:
    """Get storage instance, preferring boto3-based service if available."""
    global _storage
    if _storage is not None:
        return _storage
    
    # Try to use existing StorageService if available
    try:
        from app.storage.storage_service import get_storage_service
        storage_service = get_storage_service()
        _storage = Boto3StorageAdapter(storage_service)
        logger.info("Using Boto3StorageAdapter (MinIO/S3)")
        return _storage
    except Exception as e:
        logger.warning(f"Could not initialize Boto3StorageAdapter: {e}. Falling back to LocalStorage.")
        _storage = LocalStorage(STORAGE_BASE)
        return _storage


def save_json_to_storage(key: str, obj: Any) -> None:
    """Helper to save json artifact."""
    storage = get_storage()
    data = json.dumps(obj, ensure_ascii=False, indent=None).encode("utf-8")
    storage.put_bytes(key, data)
    logger.debug("Saved JSON artifact %s", key)


def save_ocr_result_metadata(job_id: str, page_key: str, ocr_regions: list) -> None:
    """
    Example persistence: save OCR JSON and append metadata to results DB/file.
    Replace with DB writes in real app (Postgres).
    """
    artifact_key = f"ocr/{job_id}/{page_key.split('/')[-1]}.json"
    payload = {
        "job_id": job_id,
        "page_key": page_key,
        "ocr": ocr_regions,
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }
    save_json_to_storage(artifact_key, payload)
    logger.info("Saved OCR result artifact: %s", artifact_key)
    # In real app, write DB row referencing artifact_key and page metadata


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def ocr_task(self, job_id: str, page_key: str) -> dict:
    """
    Celery task: perform OCR on a single staged page.
    Args:
        job_id: str - job identifier
        page_key: str - storage key (e.g. staging/{job_id}/page_0.png)
    """
    logger.info("ocr_task start job=%s page=%s", job_id, page_key)
    try:
        storage = get_storage()
        image_bytes = read_bytes_from_storage(page_key, storage)
        ocr_client = get_ocr_client()
        ocr_regions = ocr_client.analyze_image_bytes(image_bytes)

        # Save OCR JSON artifact
        save_ocr_result_metadata(job_id, page_key, ocr_regions)

        # Optionally trigger semantic parse task here
        # semantic_parse_task.delay(job_id, page_key, artifact_key)
        
        logger.info("ocr_task completed job=%s page=%s regions=%d", job_id, page_key, len(ocr_regions))
        return {"ok": True, "num_regions": len(ocr_regions)}
    except Exception as exc:
        logger.exception("ocr_task failed job=%s page=%s", job_id, page_key)
        # retry with exponential backoff
        raise self.retry(exc=exc, countdown=min(60, (2 ** self.request.retries)))

