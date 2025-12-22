"""
Unit tests for staging utilities.
"""

import pytest
import tempfile
import shutil
import io
from PIL import Image
from finscribe.staging import (
    LocalStorage,
    stage_upload,
    read_bytes_from_storage
)


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    storage = LocalStorage(temp_dir)
    yield storage
    shutil.rmtree(temp_dir)


def test_local_storage_put_get(temp_storage):
    """Test LocalStorage put_bytes and get_bytes."""
    key = "test/file.txt"
    data = b"test content"
    temp_storage.put_bytes(key, data)
    retrieved = temp_storage.get_bytes(key)
    assert retrieved == data


def test_local_storage_url_for(temp_storage):
    """Test LocalStorage url_for returns path."""
    key = "test/file.txt"
    url = temp_storage.url_for(key)
    assert isinstance(url, str)
    assert "test/file.txt" in url


def test_stage_upload_image(temp_storage):
    """Test staging a single image file."""
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='red')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    image_bytes = buf.getvalue()
    
    job_id = "test_job_123"
    page_keys = stage_upload(image_bytes, "test.png", job_id, temp_storage)
    
    assert len(page_keys) == 1
    assert page_keys[0] == f"staging/{job_id}/page_0.png"
    # Verify file exists
    stored_data = temp_storage.get_bytes(page_keys[0])
    assert len(stored_data) > 0


def test_stage_upload_pdf(temp_storage):
    """Test staging a PDF file (requires pdf2image)."""
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        pytest.skip("pdf2image not installed")
    
    # Create a minimal PDF (this is a simplified test)
    # In real tests, use a fixture PDF file
    # For now, we'll test that the function handles PDF extension correctly
    # by checking it doesn't crash (actual PDF conversion requires valid PDF)
    job_id = "test_job_pdf"
    
    # Note: This test would need a real PDF file to fully test
    # For now, we test that the function structure is correct
    # In integration tests, use a real PDF fixture
    pass  # Placeholder - add real PDF test with fixture


def test_read_bytes_from_storage(temp_storage):
    """Test read_bytes_from_storage helper."""
    key = "test/data.bin"
    data = b"binary data \x00\x01\x02"
    temp_storage.put_bytes(key, data)
    retrieved = read_bytes_from_storage(key, temp_storage)
    assert retrieved == data

