import time
import json
from typing import Dict, Any

# Mock database/redis for job status
JOB_STATUS: Dict[str, Dict[str, Any]] = {}

def process_job(job_id: str, file_content: bytes, filename: str, job_type: str):
    """Simulates a long-running job for document processing."""
    
    JOB_STATUS[job_id] = {"status": "processing", "progress": 0, "result": None}
    
    # Simulate processing steps
    steps = [
        ("Uploading file", 10),
        ("Running OCR", 30),
        ("Semantic Parsing", 60),
        ("Validation & Lineage", 90),
        ("Finalizing", 100)
    ]
    
    for step, progress in steps:
        time.sleep(0.5) # Simulate work
        JOB_STATUS[job_id]["progress"] = progress
        JOB_STATUS[job_id]["status"] = f"processing: {step}"
        print(f"Job {job_id}: {step} ({progress}%)")
        
    # Mock result (in a real app, this would call the DocumentProcessor)
    mock_result = {
        "document_id": job_id,
        "status": "completed",
        "extracted_data": [
            {"field_name": "invoice_number", "value": "INV-JOB-001", "confidence": 0.99, "source_model": "PaddleOCR-VL", "lineage_id": "lineage-job-1"},
            {"field_name": "total_amount", "value": 999.99, "confidence": 0.98, "source_model": "ERNIE-4.5", "lineage_id": "lineage-job-2"},
        ],
        "raw_ocr_output": {"mock": "raw ocr data"},
        "validation_status": "validated",
        "active_learning_ready": True
    }
    
    JOB_STATUS[job_id]["status"] = "completed"
    JOB_STATUS[job_id]["progress"] = 100
    JOB_STATUS[job_id]["result"] = mock_result
    print(f"Job {job_id}: Completed")

def get_job_status(job_id: str) -> Dict[str, Any]:
    """Retrieves the current status of a job."""
    return JOB_STATUS.get(job_id, {"status": "not_found", "progress": 0, "result": None})
