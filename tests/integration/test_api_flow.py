"""Integration tests for API flow (upload → result)."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAPIFlow:
    """Integration tests for complete API flow."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_analyze_endpoint_invalid_file(self, client):
        """Test analyze endpoint with invalid file."""
        # Test with no file
        response = client.post("/api/v1/analyze")
        assert response.status_code == 422  # Validation error
        
        # Test with invalid extension (make file large enough to pass size check)
        file_content = b"x" * 200  # 200 bytes, above minimum of 100
        response = client.post(
            "/api/v1/analyze",
            files={"file": ("test.exe", file_content, "application/x-msdownload")}
        )
        assert response.status_code == 400
        response_data = response.json()
        # Error might be in "detail" or "error" field
        error_msg = response_data.get("detail", response_data.get("error", "")).lower()
        assert "unsupported" in error_msg or "extension" in error_msg
    
    def test_analyze_endpoint_valid_file(self, client):
        """Test analyze endpoint with valid file (mock mode)."""
        # Create a minimal PDF-like file content (must be >= 100 bytes to pass size validation)
        file_content = b"%PDF-1.4\n" + b"fake pdf content " * 10  # Make it > 100 bytes
        
        response = client.post(
            "/api/v1/analyze",
            files={"file": ("test_invoice.pdf", file_content, "application/pdf")}
        )
        
        # Should accept the file and create a job
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "poll_url" in data
        assert data["status"] == "queued"
        
        # Test polling for job status
        job_id = data["job_id"]
        status_response = client.get(f"/api/v1/jobs/{job_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert "status" in status_data
        assert "progress" in status_data


