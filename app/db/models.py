"""Database models for jobs, results, models, and active learning."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
import enum

from . import Base


class JobStatus(str, enum.Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    """Job table for tracking document processing jobs."""
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, nullable=False, default=JobStatus.QUEUED.value)  # Store as string for SQLite compatibility
    source_type = Column(String, nullable=True)  # upload, api, batch
    filename = Column(String, nullable=True)
    file_size = Column(JSON, nullable=True)  # Store as bytes
    checksum = Column(String, nullable=True)  # SHA256 hash
    job_metadata = Column(JSON, nullable=True)  # Additional job metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    error = Column(Text, nullable=True)  # Error message if failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    results = relationship("Result", back_populates="job", cascade="all, delete-orphan")
    active_learning_records = relationship("ActiveLearning", back_populates="job")


class Result(Base):
    """Result table for storing processed document results."""
    __tablename__ = "results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    schema_version = Column(String, nullable=False, default="1.0")
    data = Column(JSON, nullable=False)  # Structured output data
    validation = Column(JSON, nullable=True)  # Validation results
    models_used = Column(JSON, nullable=True)  # List of models used
    provenance = Column(JSON, nullable=True)  # Processing provenance/lineage
    raw_ocr_output = Column(JSON, nullable=True)  # Raw OCR JSON
    object_storage_key = Column(String, nullable=True)  # S3/MinIO key for full result JSON
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    job = relationship("Job", back_populates="results")


class Model(Base):
    """Model table for tracking AI models and versions."""
    __tablename__ = "models"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)  # e.g., "PaddleOCR-VL-0.9B"
    version = Column(String, nullable=False)  # e.g., "v1.0.0"
    model_type = Column(String, nullable=False)  # ocr, vlm, llm
    checkpoint_id = Column(String, nullable=True)  # Git commit or checkpoint hash
    dataset_ids = Column(JSON, nullable=True)  # Training dataset IDs
    model_metadata = Column(JSON, nullable=True)  # Model metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    is_active = Column(String, default="true")  # Whether model is currently active
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ActiveLearning(Base):
    """Active learning table for storing corrections and training data."""
    __tablename__ = "active_learning"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    result_id = Column(String, ForeignKey("results.id", ondelete="SET NULL"), nullable=True)
    model_version = Column(String, nullable=True)  # Model version that generated this
    original = Column(JSON, nullable=False)  # Original OCR/VLM output
    correction = Column(JSON, nullable=True)  # User corrections
    ocr_payload = Column(JSON, nullable=True)  # Full OCR output
    model_output = Column(JSON, nullable=True)  # Full model output before correction
    needs_review = Column(String, default="false")  # Whether this needs human review
    reviewed_at = Column(DateTime, nullable=True)
    exported = Column(String, default="false")  # Whether exported for training
    exported_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    job = relationship("Job", back_populates="active_learning_records")

