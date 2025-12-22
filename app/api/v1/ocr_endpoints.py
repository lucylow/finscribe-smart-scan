"""
OCR endpoints using local PaddleOCR with staging and Celery tasks.

This module provides:
- POST /api/v1/analyze-ocr: Upload document, stage pages, enqueue OCR tasks
- Uses finscribe.staging for PDF/image staging
- Uses finscribe.tasks.ocr_task for background OCR processing
"""

import os
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

from ...core.schemas import JobResponse
from finscribe.staging import stage_upload, Boto3StorageAdapter, LocalStorage
from finscribe.tasks import ocr_task

logger = logging.getLogger(__name__)
router = APIRouter()

# Configuration
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
MIN_UPLOAD_BYTES = 100
ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/jpg", "image/tiff"}
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}


def get_storage_instance():
    """Get storage instance (prefer boto3-based, fallback to local)."""
    try:
        from app.storage.storage_service import get_storage_service
        storage_service = get_storage_service()
        return Boto3StorageAdapter(storage_service)
    except Exception as e:
        logger.warning(f"Could not initialize Boto3StorageAdapter: {e}. Using LocalStorage.")
        storage_base = os.getenv("STORAGE_BASE", "./storage")
        return LocalStorage(storage_base)


@router.post("/analyze-ocr", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_document_ocr(
    file: UploadFile = File(...)
):
    """
    Upload document for OCR processing using local PaddleOCR.
    
    Flow:
    1. Validate and read file
    2. Store original to raw/{job_id}/original.ext
    3. Stage pages (PDF -> PNG per page, images -> PNG)
    4. Enqueue OCR task per page
    5. Return 202 with job_id for polling
    
    Returns 202 Accepted with job_id for status polling.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    # Validate extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validate content type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES and not any(content_type.startswith(t) for t in ALLOWED_TYPES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {content_type}. Allowed: PDF, PNG, JPG, TIFF"
        )
    
    # Read file content
    try:
        file_content = await file.read()
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}"
        )
    
    if len(file_content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )
    
    # Validate file size
    file_size_mb = len(file_content) / (1024 * 1024)
    if file_size_mb > MAX_UPLOAD_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large: {file_size_mb:.1f}MB. Maximum: {MAX_UPLOAD_MB}MB"
        )
    
    if len(file_content) < MIN_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too small: {len(file_content)} bytes. Minimum: {MIN_UPLOAD_BYTES} bytes"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    try:
        # Get storage instance
        storage = get_storage_instance()
        
        # Store original file
        original_key = f"raw/{job_id}/original{file_ext}"
        storage.put_bytes(original_key, file_content)
        logger.info(f"Stored original file: {original_key}")
        
        # Stage upload (PDF -> pages, images -> single page)
        page_keys = stage_upload(file_content, file.filename, job_id, storage)
        logger.info(f"Staged {len(page_keys)} page(s) for job {job_id}")
        
        # Enqueue OCR task for each page
        for page_key in page_keys:
            try:
                ocr_task.delay(job_id, page_key)
                logger.debug(f"Enqueued OCR task for {page_key}")
            except Exception as e:
                logger.error(f"Error enqueuing OCR task for {page_key}: {e}")
                # Continue with other pages even if one fails
        
        if not page_keys:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stage any pages from the uploaded file"
            )
        
        # Return 202 Accepted
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "job_id": job_id,
                "poll_url": f"/api/v1/jobs/{job_id}",
                "status": "queued",
                "message": f"Job received and queued. Processing {len(page_keys)} page(s)."
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analyze_document_ocr: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

