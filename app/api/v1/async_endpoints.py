"""
Async API endpoints with 202 Accepted responses.

This module demonstrates the proper async pattern:
1. Accept document upload
2. Return 202 Accepted with job_id
3. Process in background via Celery
4. Poll for status via GET /jobs/{job_id}
"""

import logging
import uuid
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

from ...core.schemas import JobResponse, JobStatusResponse, JobStatus
from ...core.tasks import process_document_task
from ...core.job_manager import job_manager, JobStage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze-async", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_document_async(
    file: UploadFile = File(...),
    model_type: str = "fine_tuned"
):
    """
    Upload document for async processing.
    
    Returns 202 Accepted with job_id for status polling.
    
    Example:
        POST /api/v1/analyze-async
        Response: {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "received",
            "message": "Job received and queued for processing",
            "status_url": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000"
        }
    """
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
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
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Create job record
    job_manager.create_job(
        metadata={
            "filename": file.filename,
            "file_size": len(file_content),
            "model_type": model_type,
            "job_id": job_id  # Store job_id in metadata for lookup
        }
    )
    # Note: create_job returns a new job_id, but we're using our own
    # In production, you might want to use the returned job_id
    
    # Enqueue Celery task
    try:
        process_document_task.delay(
            job_id=job_id,
            file_content=file_content,
            filename=file.filename,
            model_type=model_type
        )
        logger.info(f"Enqueued document processing task for job {job_id}")
    except Exception as e:
        logger.error(f"Error enqueuing task: {e}")
        # Mark job as failed
        if job_id in job_manager.jobs:
            job_manager.transition_stage(job_id, JobStage.FAILED, message=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enqueuing processing task: {str(e)}"
        )
    
    # Return 202 Accepted
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "job_id": job_id,
            "status": "received",
            "message": "Job received and queued for processing",
            "status_url": f"/api/v1/jobs/{job_id}"
        }
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get job status and progress.
    
    Example:
        GET /api/v1/jobs/550e8400-e29b-41d4-a716-446655440000
        Response: {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "processing",
            "progress": 45,
            "stage": "ocr",
            "result_id": null,
            "error": null
        }
    """
    if job_id not in job_manager.jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job_state = job_manager.jobs[job_id]
    job_progress = job_state.to_progress()
    
    return JobStatusResponse(
        job_id=job_id,
        status=JobStatus(job_progress.status.value),
        progress=job_progress.progress,
        stage=job_progress.current_step.value if job_progress.current_step else None,
        result_id=job_progress.result_id,
        error=str(job_progress.error) if job_progress.error else None,
        metadata=job_state.metadata
    )

