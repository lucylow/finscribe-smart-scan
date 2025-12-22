"""
Celery tasks for FinScribe Smart Scan.

Pipeline:
  ingest -> OCR -> semantic parse -> persist result
"""

from __future__ import annotations
import json
import os
import logging
from typing import Dict, Any

from .celery_app import celery_app
from .staging import get_storage
from .ocr_client import MockOCRClient, PaddleOCRClient
from .semantic_parse_task import parse_ocr_artifact_to_structured

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOGLEVEL", "INFO"))

storage = get_storage()

MODEL_MODE = os.getenv("MODEL_MODE", "mock").lower()

if MODEL_MODE == "paddle":
    ocr_client = PaddleOCRClient()
else:
    ocr_client = MockOCRClient()


@celery_app.task(bind=True, name="finscribe.ocr_task")
def ocr_task(self, job_id: str, page_key: str, image_storage_key: str):
    """
    Performs OCR on a single page image and saves OCR artifact.
    Automatically triggers semantic parsing.
    """
    logger.info("[OCR] job=%s key=%s", job_id, image_storage_key)

    image_bytes = storage.get_bytes(image_storage_key)
    if not image_bytes:
        raise RuntimeError(f"Image not found: {image_storage_key}")

    regions = ocr_client.analyze_image(image_bytes)

    ocr_artifact = {
        "job_id": job_id,
        "source_key": image_storage_key,
        "regions": regions,
        # Include 'ocr' key for compatibility with parse_ocr_artifact_to_structured
        "ocr": regions,
    }

    ocr_key = f"ocr/{job_id}/page_0.json"
    storage.put_bytes(ocr_key, json.dumps(ocr_artifact, indent=2).encode())

    logger.info("[OCR] saved artifact %s", ocr_key)

    # enqueue semantic parsing
    semantic_parse_task.delay(job_id, ocr_key)

    return {"job_id": job_id, "ocr_key": ocr_key}


@celery_app.task(bind=True, name="finscribe.semantic_parse_task")
def semantic_parse_task(self, job_id: str, ocr_key: str):
    """
    Parses OCR artifact into structured finance JSON.
    """
    logger.info("[PARSE] job=%s ocr_key=%s", job_id, ocr_key)

    raw = storage.get_bytes(ocr_key)
    if not raw:
        raise RuntimeError(f"OCR artifact missing: {ocr_key}")

    artifact = json.loads(raw.decode())
    structured = parse_ocr_artifact_to_structured(artifact)

    result_key = f"results/{job_id}/structured.json"
    storage.put_bytes(result_key, json.dumps(structured, indent=2).encode())

    logger.info("[PARSE] saved structured result %s", result_key)

    return {"job_id": job_id, "result_key": result_key}
