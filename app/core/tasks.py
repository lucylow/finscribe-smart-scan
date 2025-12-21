"""Celery tasks for document processing pipeline."""
import logging
import hashlib
import redis
import os
from typing import Dict, Any, Optional
from celery import Task
from datetime import datetime, timedelta
import json

from .celery_app import celery_app
from ..db import SessionLocal, get_db
from ..db.models import Job, JobStatus, Result, ActiveLearning
from ..storage.storage_service import get_storage_service

logger = logging.getLogger(__name__)

# Redis client for idempotency locks
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


class DatabaseTask(Task):
    """Base task with database session management."""
    _db = None

    def before_start(self, task_id, args, kwargs):
        """Create database session before task starts."""
        self._db = SessionLocal()

    def after_return(self, *args, **kwargs):
        """Close database session after task returns."""
        if self._db:
            self._db.close()
            self._db = None

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        if self._db:
            try:
                self._db.rollback()
            except Exception as e:
                logger.error(f"Error rolling back transaction: {str(e)}")
            finally:
                self._db.close()
                self._db = None


def get_idempotency_key(job_id: str, stage: str) -> str:
    """Generate idempotency key for task."""
    return f"idempotent:{job_id}:{stage}"


def acquire_lock(key: str, ttl: int = 3600) -> bool:
    """
    Acquire Redis lock for idempotency.
    Returns True if lock acquired, False if already locked.
    """
    try:
        return redis_client.set(key, "locked", nx=True, ex=ttl)
    except Exception as e:
        logger.error(f"Error acquiring lock {key}: {str(e)}")
        return False


def release_lock(key: str):
    """Release Redis lock."""
    try:
        redis_client.delete(key)
    except Exception as e:
        logger.warning(f"Error releasing lock {key}: {str(e)}")


@celery_app.task(bind=True, base=DatabaseTask, max_retries=3, default_retry_delay=60)
def ingest_task(self, job_id: str, file_content: bytes, filename: str, checksum: str) -> Dict[str, Any]:
    """
    Ingest task: Store raw file and create job record.
    Idempotent: Can be safely retried.
    """
    idempotency_key = get_idempotency_key(job_id, "ingest")
    
    # Check if already processed
    if not acquire_lock(idempotency_key, ttl=3600):
        logger.info(f"Task {job_id}:ingest already in progress or completed")
        # Return existing result if available
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.job_metadata and job.job_metadata.get("ingest_completed"):
                return job.job_metadata.get("ingest_result", {})
        finally:
            db.close()
        raise Exception("Task already in progress")
    
    try:
        db = SessionLocal()
        try:
            # Verify checksum
            computed_checksum = hashlib.sha256(file_content).hexdigest()
            if computed_checksum != checksum:
                raise ValueError(f"Checksum mismatch: expected {checksum}, got {computed_checksum}")
            
            # Upload to object storage
            storage = get_storage_service()
            storage_key = storage.upload_raw(file_content, filename, job_id)
            
            # Update job record
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                job = Job(
                    id=job_id,
                    status=JobStatus.PROCESSING.value,
                    filename=filename,
                    file_size=len(file_content),
                    checksum=checksum,
                    job_metadata={
                        "ingest_completed": True,
                        "ingest_result": {"storage_key": storage_key},
                        "storage_key": storage_key
                    }
                )
                db.add(job)
            else:
                job.status = JobStatus.PROCESSING.value
                job.job_metadata = job.job_metadata or {}
                job.job_metadata.update({
                    "ingest_completed": True,
                    "ingest_result": {"storage_key": storage_key},
                    "storage_key": storage_key
                })
            
            db.commit()
            
            result = {"storage_key": storage_key, "job_id": job_id}
            logger.info(f"Task {job_id}:ingest completed successfully")
            return result
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Task {job_id}:ingest failed: {str(e)}", exc_info=True)
        # Mark job as failed
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED.value
                job.error = str(e)
                db.commit()
        finally:
            db.close()
        raise
    finally:
        release_lock(idempotency_key)


@celery_app.task(bind=True, base=DatabaseTask, max_retries=3, default_retry_delay=60)
def preprocess_task(self, job_id: str, storage_key: str) -> Dict[str, Any]:
    """
    Preprocess task: Extract pages from PDF, convert to images.
    Idempotent: Can be safely retried.
    """
    idempotency_key = get_idempotency_key(job_id, "preprocess")
    
    if not acquire_lock(idempotency_key, ttl=3600):
        logger.info(f"Task {job_id}:preprocess already in progress")
        raise Exception("Task already in progress")
    
    try:
        from pdf2image import convert_from_bytes
        from io import BytesIO
        
        storage = get_storage_service()
        db = SessionLocal()
        
        try:
            # Download raw file (in production, would fetch from storage)
            # For now, assume file is available
            # TODO: Implement storage download
            
            # Update job metadata
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.job_metadata = job.job_metadata or {}
                job.job_metadata["preprocess_completed"] = True
            
            db.commit()
            
            result = {"pages": 1, "job_id": job_id}  # Mock for now
            logger.info(f"Task {job_id}:preprocess completed")
            return result
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Task {job_id}:preprocess failed: {str(e)}", exc_info=True)
        raise
    finally:
        release_lock(idempotency_key)


@celery_app.task(bind=True, base=DatabaseTask, max_retries=3, default_retry_delay=60)
def ocr_task(self, job_id: str, page_num: int, image_data: bytes) -> Dict[str, Any]:
    """
    OCR task: Run OCR on a single page.
    Idempotent: Can be safely retried.
    Map-reduce: Each page is processed independently.
    """
    idempotency_key = get_idempotency_key(job_id, f"ocr_page_{page_num}")
    
    if not acquire_lock(idempotency_key, ttl=3600):
        logger.info(f"Task {job_id}:ocr_page_{page_num} already in progress")
        raise Exception("Task already in progress")
    
    try:
        # TODO: Implement actual OCR using PaddleOCR-VL service
        # For now, return mock result
        result = {
            "job_id": job_id,
            "page_num": page_num,
            "text_blocks": [],
            "status": "success"
        }
        
        logger.info(f"Task {job_id}:ocr_page_{page_num} completed")
        return result
    except Exception as e:
        logger.error(f"Task {job_id}:ocr_page_{page_num} failed: {str(e)}", exc_info=True)
        raise
    finally:
        release_lock(idempotency_key)


@celery_app.task(bind=True, base=DatabaseTask, max_retries=3, default_retry_delay=60)
def vlm_parse_task(self, job_id: str, ocr_results: list) -> Dict[str, Any]:
    """
    VLM parse task: Parse OCR results using VLM.
    Idempotent: Can be safely retried.
    """
    idempotency_key = get_idempotency_key(job_id, "vlm_parse")
    
    if not acquire_lock(idempotency_key, ttl=3600):
        logger.info(f"Task {job_id}:vlm_parse already in progress")
        raise Exception("Task already in progress")
    
    try:
        # TODO: Implement actual VLM parsing using ERNIE service
        # For now, return mock result
        result = {
            "job_id": job_id,
            "document_type": "invoice",
            "status": "success"
        }
        
        logger.info(f"Task {job_id}:vlm_parse completed")
        return result
    except Exception as e:
        logger.error(f"Task {job_id}:vlm_parse failed: {str(e)}", exc_info=True)
        raise
    finally:
        release_lock(idempotency_key)


@celery_app.task(bind=True, base=DatabaseTask, max_retries=3, default_retry_delay=60)
def postprocess_task(self, job_id: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Postprocess task: Clean and normalize parsed data.
    Idempotent: Can be safely retried.
    """
    idempotency_key = get_idempotency_key(job_id, "postprocess")
    
    if not acquire_lock(idempotency_key, ttl=3600):
        logger.info(f"Task {job_id}:postprocess already in progress")
        raise Exception("Task already in progress")
    
    try:
        # TODO: Implement postprocessing
        result = parsed_data.copy()
        result["postprocessed"] = True
        
        logger.info(f"Task {job_id}:postprocess completed")
        return result
    except Exception as e:
        logger.error(f"Task {job_id}:postprocess failed: {str(e)}", exc_info=True)
        raise
    finally:
        release_lock(idempotency_key)


@celery_app.task(bind=True, base=DatabaseTask, max_retries=3, default_retry_delay=60)
def validate_task(self, job_id: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate task: Validate parsed data using FinancialValidator.
    Idempotent: Can be safely retried.
    """
    idempotency_key = get_idempotency_key(job_id, "validate")
    
    if not acquire_lock(idempotency_key, ttl=3600):
        logger.info(f"Task {job_id}:validate already in progress")
        raise Exception("Task already in progress")
    
    try:
        from ..validation.financial_validator import FinancialValidator
        
        validator = FinancialValidator()
        validation_result = validator.validate(parsed_data)
        
        # If validation fails or confidence is low, create active learning record
        db = SessionLocal()
        try:
            if not validation_result.get("is_valid") or validation_result.get("needs_review", False):
                active_learning = ActiveLearning(
                    job_id=job_id,
                    original=parsed_data,
                    needs_review="true"
                )
                db.add(active_learning)
                db.commit()
        finally:
            db.close()
        
        result = {
            "validation": validation_result,
            "job_id": job_id
        }
        
        logger.info(f"Task {job_id}:validate completed")
        return result
    except Exception as e:
        logger.error(f"Task {job_id}:validate failed: {str(e)}", exc_info=True)
        raise
    finally:
        release_lock(idempotency_key)


@celery_app.task(bind=True, base=DatabaseTask, max_retries=3, default_retry_delay=60)
def index_task(self, job_id: str, result_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Index task: Store final result in database and object storage.
    Idempotent: Can be safely retried.
    """
    idempotency_key = get_idempotency_key(job_id, "index")
    
    if not acquire_lock(idempotency_key, ttl=3600):
        logger.info(f"Task {job_id}:index already in progress")
        raise Exception("Task already in progress")
    
    try:
        import uuid
        db = SessionLocal()
        storage = get_storage_service()
        
        try:
            result_id = str(uuid.uuid4())
            
            # Upload result to object storage
            storage_key = storage.upload_result(result_data, job_id, result_id)
            
            # Create result record
            result_record = Result(
                id=result_id,
                job_id=job_id,
                schema_version="1.0",
                data=result_data.get("data", {}),
                validation=result_data.get("validation", {}),
                models_used=result_data.get("metadata", {}).get("models_used", []),
                raw_ocr_output=result_data.get("raw_ocr_output"),
                object_storage_key=storage_key
            )
            db.add(result_record)
            
            # Update job status
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.COMPLETED.value
            
            db.commit()
            
            result = {
                "result_id": result_id,
                "storage_key": storage_key,
                "job_id": job_id
            }
            
            logger.info(f"Task {job_id}:index completed successfully")
            return result
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Task {job_id}:index failed: {str(e)}", exc_info=True)
        # Mark job as failed
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED.value
                job.error = str(e)
                db.commit()
        finally:
            db.close()
        raise
    finally:
        release_lock(idempotency_key)


