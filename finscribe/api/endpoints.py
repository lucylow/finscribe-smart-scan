# finscribe/api/endpoints.py
"""
FastAPI endpoints for FinScribe Smart Scan.

Endpoints:
- POST /v1/analyze - Upload document (PDF/image) for OCR processing
- GET /v1/jobs/{job_id} - Get job status
- GET /v1/results/{job_id} - Get structured extraction results

This endpoint uses the `get_storage` factory defined in finscribe.staging.
"""

import os
import uuid
import logging
import json
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..staging import get_storage
from ..tasks import ocr_task
from ..pdf_utils import split_pdf_to_images
from ..db.models import Job, OCRResult, ParsedResult
from ..db import get_db_session, init_db

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOGLEVEL", "INFO"))

app = FastAPI(
    title="FinScribe Smart Scan API",
    description="OCR and semantic parsing API for financial documents",
    version="1.0.0"
)

storage = get_storage()
STAGING_PREFIX = os.getenv("STAGING_PREFIX", "staging")

# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff"
}

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")


# Response models
class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str
    poll_url: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[dict] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ResultResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "finscribe-api"}


@app.post("/v1/analyze", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze(file: UploadFile = File(...)):
    """
    Upload a document (PDF or image) for OCR and semantic parsing.
    
    Returns 202 Accepted with job_id and poll URL for async processing.
    
    Supported formats: PDF, PNG, JPEG, TIFF
    """
    # Validate filename
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File must have a filename"
        )
    
    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validate content type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES and not any(
        content_type.startswith(t.split("/")[0]) for t in ALLOWED_CONTENT_TYPES
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type: {content_type}"
        )
    
    # Generate job ID
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    
    try:
        # Read file content
        body = await file.read()
        if len(body) == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Create staging directory structure
        fname = file.filename or f"upload-{uuid.uuid4().hex}.bin"
        
        # Store original file
        original_key = f"{STAGING_PREFIX}/{job_id}/original{file_ext}"
        storage.put_bytes(original_key, body)
        
        # Create job record in database
        try:
            db = next(get_db_session())
            job = Job(id=job_id, status="pending")
            db.add(job)
            db.commit()
            db.close()
        except Exception as e:
            logger.warning(f"Failed to create job record in DB: {e}. Continuing without DB tracking.")
        
        # Handle PDFs: split into pages
        if file_ext == ".pdf":
            try:
                page_images = split_pdf_to_images(body)
                logger.info(f"Split PDF into {len(page_images)} pages")
                
                # Enqueue OCR task for each page
                for page_idx, page_bytes in enumerate(page_images):
                    page_key = f"{STAGING_PREFIX}/{job_id}/page_{page_idx}.png"
                    storage.put_bytes(page_key, page_bytes)
                    ocr_task.delay(job_id, f"page_{page_idx}", page_key)
                
            except ImportError as e:
                logger.error(f"PDF processing not available: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="PDF processing not available. Install pdf2image and poppler-utils."
                )
            except Exception as e:
                logger.error(f"Failed to process PDF: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to process PDF: {str(e)}"
                )
        else:
            # For images, store and enqueue single OCR task
            staging_key = f"{STAGING_PREFIX}/{job_id}/{fname}"
            storage.put_bytes(staging_key, body)
            ocr_task.delay(job_id, "page_0", staging_key)
        
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "job_id": job_id,
                "status": "pending",
                "message": "Job received and queued for processing",
                "poll_url": f"/v1/jobs/{job_id}"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing upload: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a processing job.
    
    Returns job status, progress information, and timestamps.
    """
    try:
        db = next(get_db_session())
        job = db.query(Job).filter(Job.id == job_id).first()
        db.close()
        
        if not job:
            # Check storage for job artifacts to infer status
            ocr_exists = storage.exists(f"ocr/{job_id}/page_0.json")
            result_exists = storage.exists(f"results/{job_id}/page_0.structured.json")
            
            if result_exists:
                status = "completed"
            elif ocr_exists:
                status = "processing"
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Job {job_id} not found"
                )
            
            return {
                "job_id": job_id,
                "status": status,
                "progress": {
                    "ocr_complete": ocr_exists,
                    "parsing_complete": result_exists
                }
            }
        
        return {
            "job_id": job.id,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": None  # TODO: add updated_at to model
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching job status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/v1/results/{job_id}", response_model=ResultResponse)
async def get_results(job_id: str):
    """
    Get structured extraction results for a completed job.
    
    Returns the parsed invoice/document data in JSON format.
    """
    try:
        # Check if job exists
        db = next(get_db_session())
        job = db.query(Job).filter(Job.id == job_id).first()
        db.close()
        
        if not job:
            # Check storage directly
            if not storage.exists(f"results/{job_id}/page_0.structured.json"):
                raise HTTPException(
                    status_code=404,
                    detail=f"Job {job_id} not found or not completed"
                )
        
        # Try to load structured result from storage
        result_key = f"results/{job_id}/page_0.structured.json"
        result_bytes = storage.get_bytes(result_key)
        
        if not result_bytes:
            raise HTTPException(
                status_code=404,
                detail=f"Results not found for job {job_id}. Job may still be processing."
            )
        
        import json
        result_data = json.loads(result_bytes.decode("utf-8"))
        
        return {
            "job_id": job_id,
            "status": "completed",
            "result": result_data
        }
    
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode result JSON: {e}")
        raise HTTPException(
            status_code=500,
            detail="Invalid result data format"
        )
    except Exception as e:
        logger.exception(f"Error fetching results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

