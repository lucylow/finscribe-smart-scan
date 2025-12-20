from fastapi.testclient import TestClient
from .main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to FinScribe AI Backend"}

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "FinScribe AI Backend is running."}

# Note: More complex tests for /analyze and /compare would require mocking
# the file upload and the background worker, which is out of scope for the
# credit limit constraint.
