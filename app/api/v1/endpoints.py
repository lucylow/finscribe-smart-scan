import json
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
from ..core.document_processor import processor
from ..core.worker import process_job, get_job_status
import uuid
from typing import List, Dict, Any

router = APIRouter()

# --- Pydantic Models for Response (Simplified for now) ---

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

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    result: AnalysisResult | None = None

class ComparisonResult(BaseModel):
    document_id: str
    status: str
    fine_tuned_result: AnalysisResult
    baseline_result: AnalysisResult
    comparison_summary: Dict[str, Any]

# --- Core Endpoints ---

@router.get("/health")
async def get_health_status():
    """Health check endpoint required by the frontend and docker-compose."""
    return {"status": "ok", "message": "FinScribe AI Backend is running."}

@router.post("/analyze", response_model=JobStatus)
async def analyze_document(file: UploadFile = File(...)):
    """
    Analyzes an uploaded document using the AI pipeline (OCR + Semantic Parsing).
    This will be updated to queue a job in the next phase.
    """
    if not file.content_type.startswith(('image/', 'application/pdf')):
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload an image or PDF.")

    # Queue the job and return the job ID
    job_id = str(uuid.uuid4())
    contents = await file.read()
    
    # In a real app, this would use a proper task queue (e.g., Celery, Redis Queue)
    # For this exercise, we use BackgroundTasks for a non-blocking call
    background_tasks.add_task(process_job, job_id, contents, file.filename, "analyze")
    
    return JobStatus(job_id=job_id, status="queued", progress=0)

@router.post("/compare", response_model=JobStatus)
async def compare_models(file: UploadFile = File(...)):
    """
    Compares the fine-tuned model result against a baseline model result.
    This will be updated to queue a job in the next phase.
    """
    if not file.content_type.startswith(('image/', 'application/pdf')):
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload an image or PDF.")

    # Queue the job and return the job ID
    job_id = str(uuid.uuid4())
    contents = await file.read()
    
    # In a real app, this would use a proper task queue (e.g., Celery, Redis Queue)
    background_tasks.add_task(process_job, job_id, contents, file.filename, "compare")
    
    return JobStatus(job_id=job_id, status="queued", progress=0)

@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status_endpoint(job_id: str):
    """Retrieves the current status and result of a background job."""
    status_data = get_job_status(job_id)
    if status_data["status"] == "not_found":
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found.")
    
    # Convert result to AnalysisResult model if completed
    result = None
    if status_data["status"] == "completed" and status_data["result"]:
        # Note: This is a simplification. In a real app, we'd need a separate
        # endpoint for comparison results or a more complex JobStatus model.
        # For now, we assume the result is an AnalysisResult for the frontend to display.
        try:
            result = AnalysisResult(**status_data["result"])
        except Exception:
            # Handle case where result is a ComparisonResult (for /compare)
            # We'll just return the raw dict for now and let the frontend handle it
            pass 
            
    return JobStatus(
        job_id=job_id,
        status=status_data["status"],
        progress=status_data["progress"],
        result=result
    )

# Future endpoints for jobs, results, etc. will be added here.
