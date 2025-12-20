"""Pytest configuration and fixtures."""
import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db import Base, get_db
from app.db.models import Job, Result, Model, ActiveLearning

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    """Create a database session for testing."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_job_data():
    """Sample job data for testing."""
    return {
        "id": "test-job-123",
        "status": "queued",
        "filename": "test_invoice.pdf",
        "file_size": 1024,
        "checksum": "abc123"
    }


@pytest.fixture
def sample_result_data():
    """Sample result data for testing."""
    return {
        "document_type": "invoice",
        "invoice_number": "INV-001",
        "total": 1000.00,
        "vendor": "Test Vendor"
    }

