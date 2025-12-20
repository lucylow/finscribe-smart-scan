import os
import json
import hashlib
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid

router = APIRouter()

# --- Pydantic Models for API Contract ---

class ExtractedField(BaseModel):
    field_name: str
    value: Any
    confidence: float
    source_model: str
    lineage_id: str

class AnalysisResult(BaseModel):
    document_id: str
    status: str
    extracted_data: List[ExtractedField]
    raw_ocr_output: Dict[str, Any]
    validation_status: str
    active_learning_ready: bool = False

class JobResponse(BaseModel):
    """Response for job creation - matches API contract"""
    job_id: str
    poll_url: str
    status: str = "queued"

class JobStatus(BaseModel):
    """Job status response with progress tracking"""
    job_id: str
    status: str  # queued, processing, completed, failed
    progress: int = Field(ge=0, le=100)
    stage: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ResultResponse(BaseModel):
    """Final result response"""
    result_id: str
    job_id: str
    data: Dict[str, Any]
    validation: Dict[str, Any]
    metadata: Dict[str, Any]

# --- In-memory job store (would be Redis/DB in production) ---
from ..core.worker import JOB_STATUS, process_job

# --- Configuration ---
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/jpg", "image/tiff"}

# --- Core Endpoints ---

@router.get("/health")
async def get_health_status():
    """Health check endpoint required by the frontend and docker-compose."""
    return {
        "status": "ok", 
        "message": "FinScribe AI Backend is running.",
        "model_mode": os.getenv("MODEL_MODE", "mock")
    }

@router.post("/analyze", response_model=JobResponse)
async def analyze_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Analyzes an uploaded document using the AI pipeline (OCR + Semantic Parsing).
    Returns job_id and poll_url for async processing.
    """
    # Validate file type
    content_type = file.content_type or ""
    if not any(content_type.startswith(t.split('/')[0]) for t in ALLOWED_TYPES):
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {content_type}. Allowed: PDF, PNG, JPG, TIFF"
        )
    
    # Read and validate file size
    contents = await file.read()
    file_size_mb = len(contents) / (1024 * 1024)
    
    if file_size_mb > MAX_UPLOAD_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size_mb:.1f}MB. Maximum: {MAX_UPLOAD_MB}MB"
        )
    
    # Generate job ID and compute checksum
    job_id = str(uuid.uuid4())
    checksum = hashlib.sha256(contents).hexdigest()
    
    # Initialize job status
    JOB_STATUS[job_id] = {
        "status": "queued",
        "progress": 0,
        "stage": "received",
        "result": None,
        "error": None,
        "checksum": checksum,
        "filename": file.filename,
        "file_size": len(contents)
    }
    
    # Queue background processing
    background_tasks.add_task(process_job, job_id, contents, file.filename, "analyze")
    
    return JobResponse(
        job_id=job_id,
        poll_url=f"/api/v1/jobs/{job_id}",
        status="queued"
    )

@router.post("/compare", response_model=JobResponse)
async def compare_models(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Compares the fine-tuned model result against a baseline model result.
    Returns job_id and poll_url for async processing.
    """
    # Validate file type
    content_type = file.content_type or ""
    if not any(content_type.startswith(t.split('/')[0]) for t in ALLOWED_TYPES):
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {content_type}. Allowed: PDF, PNG, JPG, TIFF"
        )
    
    # Read file
    contents = await file.read()
    file_size_mb = len(contents) / (1024 * 1024)
    
    if file_size_mb > MAX_UPLOAD_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size_mb:.1f}MB. Maximum: {MAX_UPLOAD_MB}MB"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    checksum = hashlib.sha256(contents).hexdigest()
    
    # Initialize job status
    JOB_STATUS[job_id] = {
        "status": "queued",
        "progress": 0,
        "stage": "received",
        "result": None,
        "error": None,
        "checksum": checksum,
        "filename": file.filename
    }
    
    # Queue background processing
    background_tasks.add_task(process_job, job_id, contents, file.filename, "compare")
    
    return JobResponse(
        job_id=job_id,
        poll_url=f"/api/v1/jobs/{job_id}",
        status="queued"
    )

@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status_endpoint(job_id: str):
    """Retrieves the current status and result of a background job."""
    if job_id not in JOB_STATUS:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found.")
    
    job_data = JOB_STATUS[job_id]
    
    return JobStatus(
        job_id=job_id,
        status=job_data.get("status", "unknown"),
        progress=job_data.get("progress", 0),
        stage=job_data.get("stage"),
        result=job_data.get("result"),
        error=job_data.get("error")
    )

@router.get("/results/{result_id}", response_model=ResultResponse)
async def get_result(result_id: str):
    """Retrieves the final result of a completed job."""
    # In production, this would fetch from database
    # For now, we check if any job has this result_id
    for job_id, job_data in JOB_STATUS.items():
        result = job_data.get("result")
        if result and result.get("document_id") == result_id:
            return ResultResponse(
                result_id=result_id,
                job_id=job_id,
                data=result.get("data", {}),
                validation=result.get("validation", {"is_valid": True}),
                metadata=result.get("metadata", {})
            )
    
    raise HTTPException(status_code=404, detail=f"Result with ID {result_id} not found.")

@router.post("/results/{result_id}/corrections")
async def submit_corrections(result_id: str, corrections: Dict[str, Any]):
    """
    Accepts human corrections for active learning.
    Stores correction data for future model training.
    """
    import datetime
    
    # Find the job with this result
    job_id = None
    for jid, job_data in JOB_STATUS.items():
        result = job_data.get("result")
        if result and result.get("document_id") == result_id:
            job_id = jid
            break
    
    if not job_id:
        raise HTTPException(status_code=404, detail=f"Result with ID {result_id} not found.")
    
    # Log to active learning file
    active_learning_entry = {
        "job_id": job_id,
        "result_id": result_id,
        "model_version": "PaddleOCR-VL-0.9B",
        "ocr_payload": JOB_STATUS[job_id].get("result", {}).get("raw_ocr_output", {}),
        "model_output": JOB_STATUS[job_id].get("result", {}).get("data", {}),
        "user_correction": corrections,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    
    # Append to JSONL file
    active_learning_path = os.path.join(os.path.dirname(__file__), "../../../active_learning.jsonl")
    try:
        with open(active_learning_path, "a") as f:
            f.write(json.dumps(active_learning_entry) + "\n")
    except Exception as e:
        print(f"Warning: Could not log correction: {e}")
    
    return {"status": "recorded", "result_id": result_id}

# --- Admin Endpoints ---

@router.get("/admin/active_learning/export")
async def export_active_learning(format: str = Query("jsonl", regex="^(jsonl|json)$")):
    """Export active learning data for model training."""
    active_learning_path = os.path.join(os.path.dirname(__file__), "../../../active_learning.jsonl")
    
    if not os.path.exists(active_learning_path):
        return {"entries": [], "count": 0}
    
    entries = []
    with open(active_learning_path, "r") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    
    if format == "json":
        return {"entries": entries, "count": len(entries)}
    
    # Return as JSONL string for direct download
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content="\n".join(json.dumps(e) for e in entries),
        media_type="application/x-ndjson"
    )
