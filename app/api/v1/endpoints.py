import os
import json
import hashlib
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid

logger = logging.getLogger(__name__)
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
    markdown_output: Optional[str] = None  # Human-readable Markdown format
    output_formats: Optional[List[str]] = None  # Available output formats

# --- In-memory job store (would be Redis/DB in production) ---
from ...core.worker import JOB_STATUS, process_job, process_compare_documents_job

# --- Configuration ---
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
MIN_UPLOAD_BYTES = 100  # Minimum file size (100 bytes)
ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/jpg", "image/tiff"}
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}

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
    try:
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
                detail=f"Unsupported file extension: {file_ext}. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Validate file type
        content_type = file.content_type or ""
        if content_type not in ALLOWED_TYPES and not any(content_type.startswith(t) for t in ALLOWED_TYPES):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {content_type}. Allowed: PDF, PNG, JPG, TIFF"
            )
        
        # Read and validate file size
        try:
            contents = await file.read()
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail="Failed to read file. File may be corrupted or inaccessible."
            )
        
        file_size = len(contents)
        file_size_mb = file_size / (1024 * 1024)
        
        # Validate minimum file size
        if file_size < MIN_UPLOAD_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File too small: {file_size} bytes. Minimum size: {MIN_UPLOAD_BYTES} bytes"
            )
        
        # Validate maximum file size
        if file_size_mb > MAX_UPLOAD_MB:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {file_size_mb:.1f}MB. Maximum: {MAX_UPLOAD_MB}MB"
            )
        
        # Generate job ID and compute checksum
        try:
            job_id = str(uuid.uuid4())
            checksum = hashlib.sha256(contents).hexdigest()
        except Exception as e:
            logger.error(f"Error generating job ID or checksum: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize job. Please try again."
            )
        
        # Initialize job status
        try:
            JOB_STATUS[job_id] = {
                "status": "queued",
                "progress": 0,
                "stage": "received",
                "result": None,
                "error": None,
                "checksum": checksum,
                "filename": file.filename,
                "file_size": file_size
            }
        except Exception as e:
            logger.error(f"Error initializing job status: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize job status. Please try again."
            )
        
        # Queue background processing
        try:
            background_tasks.add_task(process_job, job_id, contents, file.filename, "analyze")
        except Exception as e:
            logger.error(f"Error queueing background task: {str(e)}")
            # Clean up job status
            JOB_STATUS.pop(job_id, None)
            raise HTTPException(
                status_code=500,
                detail="Failed to queue processing task. Please try again."
            )
        
        return JobResponse(
            job_id=job_id,
            poll_url=f"/api/v1/jobs/{job_id}",
            status="queued"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in analyze_document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your request."
        )

@router.post("/compare-documents", response_model=JobResponse)
async def compare_documents(
    background_tasks: BackgroundTasks,
    file1: UploadFile = File(..., description="First document (e.g., Quote/Proposal)"),
    file2: UploadFile = File(..., description="Second document (e.g., Invoice)")
):
    """
    Compare two documents side-by-side using multimodal reasoning.
    Useful for comparing quotes with invoices, proposals with contracts, etc.
    Returns job_id and poll_url for async processing.
    """
    try:
        # Validate both files
        for idx, file in enumerate([file1, file2], 1):
            file_label = f"File {idx}"
            
            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail=f"{file_label} must have a filename"
                )
            
            # Validate file extension
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"{file_label} has unsupported extension: {file_ext}. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
                )
            
            # Validate file type
            content_type = file.content_type or ""
            if content_type not in ALLOWED_TYPES and not any(content_type.startswith(t) for t in ALLOWED_TYPES):
                raise HTTPException(
                    status_code=400,
                    detail=f"{file_label} has unsupported file type: {content_type}. Allowed: PDF, PNG, JPG, TIFF"
                )
        
        # Read both files
        try:
            contents1 = await file1.read()
            contents2 = await file2.read()
        except Exception as e:
            logger.error(f"Error reading files: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail="Failed to read file(s). File(s) may be corrupted or inaccessible."
            )
        
        file_size1 = len(contents1)
        file_size2 = len(contents2)
        file_size_mb1 = file_size1 / (1024 * 1024)
        file_size_mb2 = file_size2 / (1024 * 1024)
        
        # Validate file sizes
        for idx, (file_size, file_size_mb, filename) in enumerate(
            [(file_size1, file_size_mb1, file1.filename), (file_size2, file_size_mb2, file2.filename)], 1
        ):
            if file_size < MIN_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {idx} ({filename}) too small: {file_size} bytes. Minimum size: {MIN_UPLOAD_BYTES} bytes"
                )
            if file_size_mb > MAX_UPLOAD_MB:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {idx} ({filename}) too large: {file_size_mb:.1f}MB. Maximum: {MAX_UPLOAD_MB}MB"
                )
        
        # Generate job ID
        try:
            job_id = str(uuid.uuid4())
            checksum1 = hashlib.sha256(contents1).hexdigest()
            checksum2 = hashlib.sha256(contents2).hexdigest()
        except Exception as e:
            logger.error(f"Error generating job ID or checksum: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize job. Please try again."
            )
        
        # Initialize job status
        try:
            JOB_STATUS[job_id] = {
                "status": "queued",
                "progress": 0,
                "stage": "received",
                "result": None,
                "error": None,
                "checksum1": checksum1,
                "checksum2": checksum2,
                "filename1": file1.filename,
                "filename2": file2.filename,
                "file_size1": file_size1,
                "file_size2": file_size2,
                "job_type": "compare_documents"
            }
        except Exception as e:
            logger.error(f"Error initializing job status: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize job status. Please try again."
            )
        
        # Queue background processing
        try:
            # Store file contents temporarily (in production, use proper storage)
            background_tasks.add_task(
                process_compare_documents_job, 
                job_id, 
                contents1, 
                file1.filename,
                contents2,
                file2.filename
            )
        except Exception as e:
            logger.error(f"Error queueing background task: {str(e)}")
            JOB_STATUS.pop(job_id, None)
            raise HTTPException(
                status_code=500,
                detail="Failed to queue processing task. Please try again."
            )
        
        return JobResponse(
            job_id=job_id,
            poll_url=f"/api/v1/jobs/{job_id}",
            status="queued"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in compare_documents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your request."
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
    try:
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
                detail=f"Unsupported file extension: {file_ext}. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Validate file type
        content_type = file.content_type or ""
        if content_type not in ALLOWED_TYPES and not any(content_type.startswith(t) for t in ALLOWED_TYPES):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {content_type}. Allowed: PDF, PNG, JPG, TIFF"
            )
        
        # Read file
        try:
            contents = await file.read()
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail="Failed to read file. File may be corrupted or inaccessible."
            )
        
        file_size = len(contents)
        file_size_mb = file_size / (1024 * 1024)
        
        # Validate minimum file size
        if file_size < MIN_UPLOAD_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"File too small: {file_size} bytes. Minimum size: {MIN_UPLOAD_BYTES} bytes"
            )
        
        # Validate maximum file size
        if file_size_mb > MAX_UPLOAD_MB:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {file_size_mb:.1f}MB. Maximum: {MAX_UPLOAD_MB}MB"
            )
        
        # Generate job ID
        try:
            job_id = str(uuid.uuid4())
            checksum = hashlib.sha256(contents).hexdigest()
        except Exception as e:
            logger.error(f"Error generating job ID or checksum: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize job. Please try again."
            )
        
        # Initialize job status
        try:
            JOB_STATUS[job_id] = {
                "status": "queued",
                "progress": 0,
                "stage": "received",
                "result": None,
                "error": None,
                "checksum": checksum,
                "filename": file.filename,
                "file_size": file_size
            }
        except Exception as e:
            logger.error(f"Error initializing job status: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize job status. Please try again."
            )
        
        # Queue background processing
        try:
            background_tasks.add_task(process_job, job_id, contents, file.filename, "compare")
        except Exception as e:
            logger.error(f"Error queueing background task: {str(e)}")
            # Clean up job status
            JOB_STATUS.pop(job_id, None)
            raise HTTPException(
                status_code=500,
                detail="Failed to queue processing task. Please try again."
            )
        
        return JobResponse(
            job_id=job_id,
            poll_url=f"/api/v1/jobs/{job_id}",
            status="queued"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in compare_models: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your request."
        )

@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status_endpoint(job_id: str):
    """Retrieves the current status and result of a background job."""
    try:
        # Validate job_id format (basic UUID validation)
        try:
            uuid.UUID(job_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid job ID format: {job_id}"
            )
        
        if job_id not in JOB_STATUS:
            raise HTTPException(
                status_code=404,
                detail=f"Job with ID {job_id} not found. It may have expired or never existed."
            )
        
        job_data = JOB_STATUS[job_id]
        
        return JobStatus(
            job_id=job_id,
            status=job_data.get("status", "unknown"),
            progress=job_data.get("progress", 0),
            stage=job_data.get("stage"),
            result=job_data.get("result"),
            error=job_data.get("error")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting job status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving job status."
        )

@router.get("/results/{result_id}", response_model=ResultResponse)
async def get_result(result_id: str):
    """Retrieves the final result of a completed job."""
    try:
        # Validate result_id format (basic UUID validation)
        try:
            uuid.UUID(result_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid result ID format: {result_id}"
            )
        
        # In production, this would fetch from database
        # For now, we check if any job has this result_id
        for job_id, job_data in JOB_STATUS.items():
            try:
                result = job_data.get("result")
                if result and result.get("document_id") == result_id:
                    return ResultResponse(
                        result_id=result_id,
                        job_id=job_id,
                        data=result.get("data", {}),
                        validation=result.get("validation", {"is_valid": True}),
                        metadata=result.get("metadata", {}),
                        markdown_output=result.get("markdown_output"),
                        output_formats=result.get("metadata", {}).get("output_formats", ["json"])
                    )
            except Exception as e:
                logger.warning(f"Error processing job {job_id} for result {result_id}: {str(e)}")
                continue
        
        raise HTTPException(
            status_code=404,
            detail=f"Result with ID {result_id} not found. It may have expired or the job may not be completed."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting result: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while retrieving the result."
        )

@router.get("/results/{result_id}/download")
async def download_result(result_id: str, format: str = "json"):
    """
    Download result in specified format (json or markdown).
    Returns the structured output in the requested format for easy export.
    """
    from fastapi.responses import Response
    
    try:
        # Validate result_id format
        try:
            uuid.UUID(result_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid result ID format: {result_id}"
            )
        
        # Validate format
        if format not in ["json", "markdown"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {format}. Supported formats: json, markdown"
            )
        
        # Find the job with this result
        result_data = None
        for job_id, job_data in JOB_STATUS.items():
            try:
                result = job_data.get("result")
                if result and result.get("document_id") == result_id:
                    result_data = result
                    break
            except Exception as e:
                logger.warning(f"Error processing job {job_id} for download: {str(e)}")
                continue
        
        if not result_data:
            raise HTTPException(
                status_code=404,
                detail=f"Result with ID {result_id} not found. It may have expired or the job may not be completed."
            )
        
        # Generate file content based on format
        if format == "json":
            json_data = result_data.get("data", {})
            content = json.dumps(json_data, indent=2, ensure_ascii=False)
            return Response(
                content=content,
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="result_{result_id}.json"'
                }
            )
        elif format == "markdown":
            markdown_content = result_data.get("markdown_output", "")
            if not markdown_content:
                # Fallback: generate markdown from JSON data if not available
                from app.core.post_processing import FinancialDocumentPostProcessor
                post_processor = FinancialDocumentPostProcessor()
                structured_data = {
                    "success": True,
                    "data": result_data.get("data", {}),
                    "validation": result_data.get("validation", {}),
                    "metadata": result_data.get("metadata", {})
                }
                markdown_content = post_processor.generate_markdown(structured_data)
            
            return Response(
                content=markdown_content,
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f'attachment; filename="result_{result_id}.md"'
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error downloading result: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while downloading the result."
        )

@router.post("/results/{result_id}/corrections")
async def submit_corrections(result_id: str, corrections: Dict[str, Any]):
    """
    Accepts human corrections for active learning.
    Stores correction data for future model training.
    """
    import datetime
    
    try:
        # Validate result_id format
        try:
            uuid.UUID(result_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid result ID format: {result_id}"
            )
        
        # Validate corrections payload
        if not isinstance(corrections, dict):
            raise HTTPException(
                status_code=400,
                detail="Corrections must be a JSON object"
            )
        
        if not corrections:
            raise HTTPException(
                status_code=400,
                detail="Corrections cannot be empty"
            )
        
        # Find the job with this result
        job_id = None
        for jid, job_data in JOB_STATUS.items():
            try:
                result = job_data.get("result")
                if result and result.get("document_id") == result_id:
                    job_id = jid
                    break
            except Exception as e:
                logger.warning(f"Error processing job {jid} for corrections: {str(e)}")
                continue
        
        if not job_id:
            raise HTTPException(
                status_code=404,
                detail=f"Result with ID {result_id} not found. Please ensure the job is completed."
            )
        
        # Log to active learning file
        try:
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
            active_learning_path = os.path.join(os.path.dirname(__file__), "../../../data/active_learning.jsonl")
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(active_learning_path), exist_ok=True)
                with open(active_learning_path, "a") as f:
                    f.write(json.dumps(active_learning_entry) + "\n")
                logger.info(f"Successfully logged correction for result {result_id}")
            except (IOError, OSError) as e:
                logger.error(f"Could not write to active learning file: {str(e)}")
                # Don't fail the request if logging fails
        except Exception as e:
            logger.error(f"Error preparing active learning entry: {str(e)}")
            # Don't fail the request if logging fails
        
        return {"status": "recorded", "result_id": result_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error submitting corrections: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while submitting corrections."
        )

# --- Admin Endpoints ---

@router.get("/admin/active_learning/export")
async def export_active_learning(format: str = Query("jsonl", regex="^(jsonl|json)$")):
    """Export active learning data for model training."""
    try:
        active_learning_path = os.path.join(os.path.dirname(__file__), "../../../data/active_learning.jsonl")
        
        if not os.path.exists(active_learning_path):
            return {"entries": [], "count": 0}
        
        entries = []
        line_number = 0
        try:
            with open(active_learning_path, "r") as f:
                for line_number, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            logger.warning(f"Error parsing JSON at line {line_number}: {str(e)}")
                            # Skip invalid lines but continue processing
                            continue
        except (IOError, OSError) as e:
            logger.error(f"Error reading active learning file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to read active learning data file."
            )
        
        if format == "json":
            return {"entries": entries, "count": len(entries)}
        
        # Return as JSONL string for direct download
        from fastapi.responses import PlainTextResponse
        try:
            content = "\n".join(json.dumps(e) for e in entries)
            return PlainTextResponse(
                content=content,
                media_type="application/x-ndjson"
            )
        except (TypeError, ValueError) as e:
            logger.error(f"Error serializing active learning data: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to serialize active learning data."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error exporting active learning data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while exporting active learning data."
        )
