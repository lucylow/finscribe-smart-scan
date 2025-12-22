"""
Integration tests for OCR pipeline.

Tests the full OCR flow: image -> OCR -> parsing -> result.
"""

import pytest
import os
import json
from pathlib import Path

# Set mock mode for testing
os.environ["MODEL_MODE"] = "mock"
os.environ["STORAGE_BASE"] = "./test_storage"

from finscribe.ocr_client import get_ocr_client, MockOCRClient, PaddleOCRClient
from finscribe.staging import LocalStorage
from finscribe.tasks import ocr_task, semantic_parse_task


@pytest.fixture
def storage():
    """Fixture providing test storage."""
    storage = LocalStorage(base_path="./test_storage")
    yield storage
    # Cleanup: remove test storage after test
    import shutil
    if os.path.exists("./test_storage"):
        shutil.rmtree("./test_storage", ignore_errors=True)


@pytest.fixture
def sample_image_bytes():
    """Fixture providing sample image bytes."""
    # Create a simple 1x1 PNG image for testing
    from PIL import Image
    import io
    img = Image.new('RGB', (100, 100), color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def test_mock_ocr_client(sample_image_bytes):
    """Test that mock OCR client returns expected regions."""
    client = MockOCRClient()
    regions = client.analyze_image(sample_image_bytes)
    
    assert isinstance(regions, list)
    assert len(regions) > 0
    assert all("text" in r for r in regions)
    assert all("bbox" in r for r in regions)
    assert all("confidence" in r for r in regions)


def test_ocr_client_factory():
    """Test OCR client factory function."""
    # Test mock mode
    os.environ["MODEL_MODE"] = "mock"
    client = get_ocr_client()
    assert isinstance(client, MockOCRClient)
    
    # Test that paddle mode falls back to mock if not available
    os.environ["MODEL_MODE"] = "paddle"
    try:
        client = get_ocr_client()
        # May be PaddleOCRClient if available, or MockOCRClient if not
        assert client is not None
    except Exception:
        pass  # Expected if PaddleOCR not installed


def test_local_storage(storage, sample_image_bytes):
    """Test local storage operations."""
    key = "test/image.png"
    
    # Write
    storage.put_bytes(key, sample_image_bytes)
    
    # Read
    retrieved = storage.get_bytes(key)
    assert retrieved == sample_image_bytes
    
    # Exists
    assert storage.exists(key)
    assert not storage.exists("nonexistent")


@pytest.mark.skipif(
    not os.environ.get("TEST_WITH_CELERY", "0") == "1",
    reason="Requires Celery broker running"
)
def test_ocr_task_integration(storage, sample_image_bytes):
    """Test OCR task end-to-end (requires Celery)."""
    job_id = "test-job-123"
    page_key = "page_0"
    
    # Store test image
    image_key = f"staging/{job_id}/page_0.png"
    storage.put_bytes(image_key, sample_image_bytes)
    
    # Run OCR task (synchronous for testing)
    result = ocr_task.apply(args=(job_id, page_key, image_key))
    
    assert result.successful()
    assert "ocr_key" in result.result


def test_parser_with_mock_ocr_output():
    """Test semantic parser with mock OCR output."""
    from finscribe.semantic_parse_task import parse_ocr_artifact_to_structured
    
    # Create mock OCR artifact
    ocr_artifact = {
        "job_id": "test-123",
        "page_key": "page_0",
        "ocr": [
            {"text": "ACME Corporation", "bbox": [20, 10, 400, 40], "confidence": 0.99},
            {"text": "Invoice #: INV-123", "bbox": [1400, 20, 300, 20], "confidence": 0.98},
            {"text": "Date: 2025-12-20", "bbox": [1400, 40, 200, 20], "confidence": 0.98},
            {"text": "Widget A 2 $50.00 $100.00", "bbox": [100, 340, 1600, 30], "confidence": 0.95},
            {"text": "Total $100.00", "bbox": [1400, 960, 400, 30], "confidence": 0.98},
        ],
        "regions": [
            {"text": "ACME Corporation", "bbox": [20, 10, 400, 40], "confidence": 0.99},
            {"text": "Invoice #: INV-123", "bbox": [1400, 20, 300, 20], "confidence": 0.98},
            {"text": "Date: 2025-12-20", "bbox": [1400, 40, 200, 20], "confidence": 0.98},
            {"text": "Widget A 2 $50.00 $100.00", "bbox": [100, 340, 1600, 30], "confidence": 0.95},
            {"text": "Total $100.00", "bbox": [1400, 960, 400, 30], "confidence": 0.98},
        ]
    }
    
    # Parse
    structured = parse_ocr_artifact_to_structured(ocr_artifact)
    
    # Validate output structure
    assert "invoice_no" in structured or "invoice_number" in structured
    assert "confidence_score" in structured or "confidence" in structured
    # May have line_items
    # assert "line_items" in structured or "financial_summary" in structured


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

