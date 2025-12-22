"""
Unit tests for OCR client implementations.
"""

import pytest
import os
from finscribe.ocr_client import (
    OCRClientBase,
    MockOCRClient,
    PaddleOCRClient,
    get_ocr_client
)


def test_mock_ocr_client():
    """Test MockOCRClient returns deterministic results."""
    client = MockOCRClient()
    # Use a dummy byte string
    image_bytes = b"fake_image_data"
    result = client.analyze_image_bytes(image_bytes)
    
    assert isinstance(result, list)
    assert len(result) > 0
    for region in result:
        assert "text" in region
        assert "bbox" in region
        assert "confidence" in region
        assert isinstance(region["text"], str)
        assert isinstance(region["bbox"], list)
        assert len(region["bbox"]) == 4
        assert isinstance(region["confidence"], float)
        assert 0.0 <= region["confidence"] <= 1.0


def test_mock_ocr_client_deterministic():
    """Test MockOCRClient returns same results for same input."""
    client = MockOCRClient()
    image_bytes = b"test"
    result1 = client.analyze_image_bytes(image_bytes)
    result2 = client.analyze_image_bytes(image_bytes)
    assert result1 == result2


@pytest.mark.skipif(
    os.getenv("OCR_MODE", "mock") == "mock",
    reason="PaddleOCR not installed or OCR_MODE=mock"
)
def test_paddle_ocr_client():
    """Test PaddleOCRClient (requires paddleocr installed)."""
    # This test will be skipped if PaddleOCR is not available
    try:
        client = PaddleOCRClient(lang="en", use_gpu=False)
        # Use a small test image (1x1 pixel PNG)
        # In real tests, use a fixture image
        import io
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        image_bytes = buf.getvalue()
        
        result = client.analyze_image_bytes(image_bytes)
        assert isinstance(result, list)
        # PaddleOCR may return empty list for blank image, which is fine
    except ImportError:
        pytest.skip("PaddleOCR not installed")


def test_get_ocr_client_mock():
    """Test factory returns MockOCRClient when OCR_MODE=mock."""
    os.environ["OCR_MODE"] = "mock"
    client = get_ocr_client()
    assert isinstance(client, MockOCRClient)
    # Clean up
    if "OCR_MODE" in os.environ:
        del os.environ["OCR_MODE"]


def test_get_ocr_client_invalid_mode():
    """Test factory raises ValueError for invalid mode."""
    os.environ["OCR_MODE"] = "invalid"
    with pytest.raises(ValueError):
        get_ocr_client()
    # Clean up
    if "OCR_MODE" in os.environ:
        del os.environ["OCR_MODE"]

