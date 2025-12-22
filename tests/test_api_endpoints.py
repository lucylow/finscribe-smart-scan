"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import io

from app.main import app
from app.db import Base, get_db
from app.storage import reset_storage


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Reset storage
    reset_storage()
    
    def override_get_db():
        try:
            yield session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client(db_session):
    """Create a test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_analyze_endpoint_invalid_file(client):
    """Test analyze endpoint with invalid file."""
    # Missing file
    response = client.post("/api/v1/analyze")
    assert response.status_code == 422  # Validation error
    
    # Invalid file type
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.exe", b"content", "application/x-msdownload")}
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


def test_analyze_endpoint_valid_file(client):
    """Test analyze endpoint with valid file."""
    # Create a simple PDF-like file
    file_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
    
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.pdf", file_content, "application/pdf")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert "poll_url" in data
    assert data["status"] == "queued"
    
    job_id = data["job_id"]
    
    # Check job status
    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    status_data = response.json()
    assert status_data["job_id"] == job_id
    assert status_data["status"] in ["queued", "processing", "completed", "failed"]


def test_get_job_status_not_found(client):
    """Test getting job status for non-existent job."""
    response = client.get("/api/v1/jobs/non-existent-id")
    assert response.status_code == 404


def test_get_result_not_found(client):
    """Test getting result for non-existent result."""
    response = client.get("/api/v1/results/non-existent-id")
    assert response.status_code == 404

