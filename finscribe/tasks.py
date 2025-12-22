"""
Celery tasks for FinScribe Smart Scan.

Pipeline:
  ingest -> OCR -> semantic parse -> persist result
"""

from __future__ import annotations
import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .celery_app import celery_app
from .staging import get_storage
from .ocr_client import get_ocr_client
from .semantic_parse_task import parse_ocr_artifact_to_structured
from .db.models import Job, OCRResult, ParsedResult
from .db import get_db_session

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOGLEVEL", "INFO"))

storage = get_storage()

# Get OCR client using factory function
ocr_client = get_ocr_client()


@celery_app.task(bind=True, name="finscribe.ocr_task")
def ocr_task(self, job_id: str, page_key: str, image_storage_key: str):
    """
    Performs OCR on a single page image and saves OCR artifact.
    Automatically triggers semantic parsing.
    
    Args:
        job_id: Job identifier
        page_key: Page identifier (e.g., "page_0", "page_1")
        image_storage_key: Storage key for the image to process
    """
    logger.info("[OCR] job=%s page=%s key=%s", job_id, page_key, image_storage_key)

    # Update job status
    try:
        db = next(get_db_session())
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "processing"
            db.commit()
        db.close()
    except Exception as e:
        logger.warning(f"Failed to update job status: {e}")

    # Get image bytes
    image_bytes = storage.get_bytes(image_storage_key)
    if not image_bytes:
        raise RuntimeError(f"Image not found: {image_storage_key}")

    # Run OCR
    regions = ocr_client.analyze_image(image_bytes)
    logger.info(f"[OCR] Found {len(regions)} text regions")

    # Create OCR artifact
    ocr_artifact = {
        "job_id": job_id,
        "page_key": page_key,
        "source_key": image_storage_key,
        "regions": regions,
        # Include 'ocr' key for compatibility with parse_ocr_artifact_to_structured
        "ocr": regions,
        "processed_at": datetime.utcnow().isoformat() + "Z"
    }

    # Save OCR artifact to storage
    ocr_key = f"ocr/{job_id}/{page_key}.json"
    storage.put_bytes(ocr_key, json.dumps(ocr_artifact, indent=2).encode())
    logger.info("[OCR] saved artifact %s", ocr_key)

    # Persist OCR result to database
    try:
        db = next(get_db_session())
        ocr_result = OCRResult(
            id=f"{job_id}_{page_key}",
            job_id=job_id,
            page_index=page_key,
            data=ocr_artifact
        )
        db.add(ocr_result)
        db.commit()
        db.close()
    except Exception as e:
        logger.warning(f"Failed to persist OCR result to DB: {e}")

    # Enqueue semantic parsing
    semantic_parse_task.delay(job_id, page_key, ocr_key)

    return {"job_id": job_id, "ocr_key": ocr_key, "regions_count": len(regions)}


@celery_app.task(bind=True, name="finscribe.semantic_parse_task", max_retries=2)
def semantic_parse_task(self, job_id: str, page_key: str, ocr_key: Optional[str] = None):
    """
    Parses OCR artifact into structured finance JSON.
    
    Args:
        job_id: Job identifier
        page_key: Page identifier (e.g., "page_0")
        ocr_key: Optional explicit OCR artifact key (defaults to inferred key)
    """
    logger.info("[PARSE] job=%s page=%s ocr_key=%s", job_id, page_key, ocr_key)

    # Infer OCR key if not provided
    if ocr_key is None:
        ocr_key = f"ocr/{job_id}/{page_key}.json"

    # Load OCR artifact
    raw = storage.get_bytes(ocr_key)
    if not raw:
        logger.error(f"OCR artifact missing: {ocr_key}")
        # Update job status to failed
        try:
            db = next(get_db_session())
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                db.commit()
            db.close()
        except Exception as db_err:
            logger.warning(f"Failed to update job status: {db_err}")
        raise RuntimeError(f"OCR artifact missing: {ocr_key}")

    artifact = json.loads(raw.decode())
    
    # Parse to structured format using the parse function
    try:
        structured = parse_ocr_artifact_to_structured(artifact)
    except Exception as e:
        logger.exception(f"Parsing failed for job {job_id}: {e}")
        # Update job status to failed
        try:
            db = next(get_db_session())
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
            # Store error in parsed result
            parsed_result = ParsedResult(
                id=f"{job_id}_{page_key}",
                job_id=job_id,
                structured=None,
                ocr_json=artifact,
                error=str(e)
            )
            db.add(parsed_result)
            db.commit()
            db.close()
        except Exception as db_err:
            logger.warning(f"Failed to update job status: {db_err}")
        raise

    # Save structured result to storage
    result_key = f"results/{job_id}/{page_key}.structured.json"
    storage.put_bytes(result_key, json.dumps(structured, indent=2, ensure_ascii=False).encode())
    logger.info("[PARSE] saved structured result %s", result_key)

    # Persist to database
    try:
        db = next(get_db_session())
        # Check if result already exists
        existing = db.query(ParsedResult).filter(ParsedResult.job_id == job_id).first()
        if existing:
            existing.structured = structured
            existing.ocr_json = artifact
            existing.error = None
        else:
            parsed_result = ParsedResult(
                id=f"{job_id}_{page_key}",
                job_id=job_id,
                structured=structured,
                ocr_json=artifact
            )
            db.add(parsed_result)
        
        # Update job status to completed
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "completed"
        
        db.commit()
        db.close()
        logger.info("[PARSE] persisted result to database for job %s", job_id)
    except Exception as e:
        logger.warning(f"Failed to persist result to DB: {e}")

    return {"job_id": job_id, "result_key": result_key, "status": "completed"}
