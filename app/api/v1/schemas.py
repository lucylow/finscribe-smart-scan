"""
Strict Pydantic schemas for API contracts.
Implements canonical result schema with versioning and lineage.
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum


# ============================================================================
# Job Lifecycle & Progress Models
# ============================================================================

class JobStage(str, Enum):
    """Deterministic job state machine stages."""
    RECEIVED = "received"
    STAGING = "staging"
    PREPROCESS = "preprocess"
    OCR_LAYOUT = "ocr_layout"
    OCR_RECOGNIZE = "ocr_recognize"
    SEMANTIC_PARSE = "semantic_parse"
    POSTPROCESS = "postprocess"
    VALIDATE = "validate"
    STORE = "store"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(str, Enum):
    """Job status values."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StageInfo(BaseModel):
    """Information about a processing stage."""
    stage: JobStage
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    progress: int = Field(ge=0, le=100, default=0)
    logs: List[str] = Field(default_factory=list)
    retry_count: int = Field(ge=0, default=0)
    error: Optional[str] = None


class JobProgress(BaseModel):
    """Job progress tracking with stage information."""
    job_id: str
    status: JobStatus
    current_step: Optional[JobStage] = None
    progress: int = Field(ge=0, le=100, default=0)
    stages: List[StageInfo] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)
    result_id: Optional[str] = None
    error: Optional[Dict[str, Any]] = None  # {code, message, retriable}


# ============================================================================
# Request Models
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request model for document analysis."""
    mode: Literal["sync", "async"] = Field(default="async")
    metadata: Optional[Dict[str, Any]] = None
    callback_url: Optional[HttpUrl] = None
    tags: Optional[List[str]] = None
    pii_redaction: bool = Field(default=False)


class CompareRequest(BaseModel):
    """Request model for document comparison."""
    file1_id: Optional[str] = None  # result_id or job_id
    file2_id: Optional[str] = None  # result_id or job_id
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Response Models
# ============================================================================

class JobResponse(BaseModel):
    """Response for job creation."""
    job_id: str
    status: Literal["queued"] = "queued"
    poll_url: str
    stream_url: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Response for analyze endpoint - can be 200 or 202."""
    job_id: Optional[str] = None
    status: Literal["queued", "completed"]
    result_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    downloads: Optional[Dict[str, str]] = None  # {json: url, csv: url}
    poll_url: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Response for GET /api/v1/jobs/{job_id}."""
    job_id: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    current_step: Optional[JobStage] = None
    logs: List[str] = Field(default_factory=list)
    result_id: Optional[str] = None
    error: Optional[Dict[str, Any]] = None


# ============================================================================
# Result Schema with Versioning & Lineage
# ============================================================================

class ModelInfo(BaseModel):
    """Information about a model used in processing."""
    name: str
    version: str
    confidence: Optional[float] = None
    latency_ms: Optional[int] = None


class Provenance(BaseModel):
    """Provenance information for extracted data."""
    source_type: str  # multipart, s3, imap, local
    source_id: Optional[str] = None
    filename: str
    checksum: str
    ingest_time: datetime
    user_id: Optional[str] = None
    tags: Optional[List[str]] = None


class FieldExtraction(BaseModel):
    """Extracted field with confidence and provenance."""
    field_name: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    source_model: str
    lineage_id: str
    bbox: Optional[List[float]] = None  # [x1, y1, x2, y2]
    page: Optional[int] = None


class FinancialSummary(BaseModel):
    """Financial summary from document."""
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    tax_rate: Optional[float] = None
    total: Optional[float] = None
    currency: Optional[str] = None
    line_items_count: Optional[int] = None


class ValidationResult(BaseModel):
    """Validation results."""
    is_valid: bool
    math_ok: bool
    dates_ok: bool
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    field_confidences: Dict[str, float] = Field(default_factory=dict)
    needs_review: bool = False


class ResultResponse(BaseModel):
    """Structured result response with schema versioning."""
    schema_version: str = Field(default="1.0")
    result_id: str
    job_id: str
    document_metadata: Dict[str, Any] = Field(default_factory=dict)
    extracted_fields: List[FieldExtraction] = Field(default_factory=list)
    financial_summary: Optional[FinancialSummary] = None
    validation_results: Optional[ValidationResult] = None
    models_used: List[ModelInfo] = Field(default_factory=list)
    provenance: Provenance
    created_at: datetime
    processing_time_ms: Optional[int] = None
    markdown_output: Optional[str] = None  # Human-readable Markdown format
    output_formats: List[str] = Field(default_factory=lambda: ["json"])  # Available output formats


# ============================================================================
# Comparison Models
# ============================================================================

class ComparisonSummary(BaseModel):
    """Summary of comparison between two results."""
    comparison_id: str
    summary: str
    detailed: Dict[str, Any] = Field(default_factory=dict)
    differences: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_delta: Optional[float] = None


class CompareResponse(BaseModel):
    """Response for compare endpoint."""
    comparison_id: str
    summary: str
    detailed: Dict[str, Any]
    result1: Optional[ResultResponse] = None
    result2: Optional[ResultResponse] = None


# ============================================================================
# Streaming Models
# ============================================================================

class StreamEvent(BaseModel):
    """SSE/WebSocket event for job progress."""
    job_id: str
    step: JobStage
    progress: int = Field(ge=0, le=100)
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None

