"""
Pydantic schemas for job management.
"""

from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class JobStatus(str, Enum):
    """Job status enumeration."""
    
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobResponse(BaseModel):
    """Response when creating a new job."""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    message: str = Field(..., description="Human-readable message")
    status_url: str = Field(..., description="URL to check job status")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "received",
                "message": "Job received and queued for processing",
                "status_url": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )


class JobStatusResponse(BaseModel):
    """Response when checking job status."""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Progress percentage (0-100)")
    stage: Optional[str] = Field(None, description="Current processing stage")
    result_id: Optional[str] = Field(None, description="Result identifier (if completed)")
    error: Optional[str] = Field(None, description="Error message (if failed)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "progress": 45,
                "stage": "ocr",
                "result_id": None,
                "error": None
            }
        }
    )

