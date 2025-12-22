"""Tests for job service."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os

from app.db import Base
from app.db.models import Job, Result
from app.core.job_service import JobService
from app.storage import reset_storage


@pytest.fixture
def db_session():
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Reset storage to use test storage
    reset_storage()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def job_service(db_session):
    """Create a job service instance."""
    return JobService(db_session)


def test_create_job(job_service):
    """Test creating a job."""
    file_content = b"test file content"
    filename = "test.pdf"
    file_size = len(file_content)
    checksum = "abc123"
    
    job = job_service.create_job(
        filename=filename,
        file_content=file_content,
        file_size=file_size,
        checksum=checksum
    )
    
    assert job.id is not None
    assert job.filename == filename
    assert job.file_size == str(file_size)
    assert job.checksum == checksum
    assert job.status == "queued"
    assert job.progress == "0"
    assert job.stage == "received"


def test_get_job(job_service):
    """Test retrieving a job."""
    file_content = b"test content"
    job = job_service.create_job(
        filename="test.pdf",
        file_content=file_content,
        file_size=len(file_content),
        checksum="test123"
    )
    
    retrieved = job_service.get_job(job.id)
    assert retrieved is not None
    assert retrieved.id == job.id
    assert retrieved.filename == "test.pdf"


def test_update_job_status(job_service):
    """Test updating job status."""
    file_content = b"test content"
    job = job_service.create_job(
        filename="test.pdf",
        file_content=file_content,
        file_size=len(file_content),
        checksum="test123"
    )
    
    updated = job_service.update_job_status(
        job.id,
        status="processing",
        progress=50,
        stage="ocr"
    )
    
    assert updated is not None
    assert updated.status == "processing"
    assert updated.progress == "50"
    assert updated.stage == "ocr"


def test_create_result(job_service):
    """Test creating a result."""
    file_content = b"test content"
    job = job_service.create_job(
        filename="test.pdf",
        file_content=file_content,
        file_size=len(file_content),
        checksum="test123"
    )
    
    result_data = {"invoice_number": "INV-001", "total": 100.0}
    validation = {"is_valid": True}
    
    result = job_service.create_result(
        job_id=job.id,
        data=result_data,
        validation=validation
    )
    
    assert result.id is not None
    assert result.job_id == job.id
    assert result.data == result_data
    assert result.validation == validation
    
    # Verify job is marked as completed
    updated_job = job_service.get_job(job.id)
    assert updated_job.status == "completed"
    assert updated_job.progress == "100"


def test_get_result_by_job_id(job_service):
    """Test retrieving result by job ID."""
    file_content = b"test content"
    job = job_service.create_job(
        filename="test.pdf",
        file_content=file_content,
        file_size=len(file_content),
        checksum="test123"
    )
    
    result_data = {"invoice_number": "INV-001"}
    result = job_service.create_result(
        job_id=job.id,
        data=result_data
    )
    
    retrieved = job_service.get_result_by_job_id(job.id)
    assert retrieved is not None
    assert retrieved.id == result.id
    assert retrieved.data == result_data

