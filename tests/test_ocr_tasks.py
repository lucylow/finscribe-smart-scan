"""
Integration tests for OCR tasks.
"""

import pytest
import tempfile
import shutil
import os
from unittest.mock import patch, MagicMock
from finscribe.tasks import ocr_task, get_storage
from finscribe.staging import LocalStorage


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    storage = LocalStorage(temp_dir)
    yield storage
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_storage(monkeypatch, temp_storage):
    """Mock get_storage to return temp_storage."""
    def _get_storage():
        return temp_storage
    monkeypatch.setattr("finscribe.tasks.get_storage", _get_storage)
    return temp_storage


def test_ocr_task_mock_mode(mock_storage):
    """Test ocr_task with MockOCRClient."""
    # Set OCR_MODE to mock
    os.environ["OCR_MODE"] = "mock"
    
    # Create a staged image
    job_id = "test_job_1"
    page_key = f"staging/{job_id}/page_0.png"
    
    # Create a simple test image
    from PIL import Image
    import io
    img = Image.new('RGB', (100, 100), color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    mock_storage.put_bytes(page_key, buf.getvalue())
    
    # Run task synchronously (not via Celery)
    result = ocr_task.apply(args=(job_id, page_key))
    
    assert result.successful()
    assert result.result["ok"] is True
    assert "num_regions" in result.result
    
    # Verify OCR result artifact was saved
    artifact_key = f"ocr/{job_id}/page_0.png.json"
    try:
        artifact_data = mock_storage.get_bytes(artifact_key)
        assert len(artifact_data) > 0
    except FileNotFoundError:
        pytest.fail(f"OCR artifact not saved: {artifact_key}")
    
    # Clean up
    if "OCR_MODE" in os.environ:
        del os.environ["OCR_MODE"]


def test_ocr_task_retry_on_error(mock_storage):
    """Test ocr_task retries on error."""
    os.environ["OCR_MODE"] = "mock"
    
    job_id = "test_job_2"
    page_key = "staging/nonexistent/page.png"
    
    # Task should fail and retry
    result = ocr_task.apply(args=(job_id, page_key))
    
    # Task should have failed after retries
    assert not result.successful()
    
    # Clean up
    if "OCR_MODE" in os.environ:
        del os.environ["OCR_MODE"]

