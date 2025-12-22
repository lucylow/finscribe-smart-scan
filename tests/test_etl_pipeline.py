"""
Tests for ETL pipeline components.
"""
import pytest
import tempfile
import os
import cv2
import numpy as np
from pathlib import Path

from data_pipeline.ingestion import ingest_from_local, ingest_from_bytes
from data_pipeline.preprocess import preprocess
from data_pipeline.normalizer import normalize_date, normalize_currency, normalize_invoice_data
from data_pipeline.validator import validate, check_arithmetic
from data_pipeline.utils import generate_id, safe_cast, timestamp


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_image(temp_dir):
    """Create a sample image file for testing."""
    img_path = os.path.join(temp_dir, "test_image.png")
    # Create a simple black image
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.imwrite(img_path, img)
    return img_path


def test_ingest_local(sample_image, temp_dir):
    """Test local file ingestion."""
    # Create a copy in temp_dir
    dest = os.path.join(temp_dir, "test_copy.png")
    with open(sample_image, "rb") as src, open(dest, "wb") as dst:
        dst.write(src.read())
    
    result = ingest_from_local(dest)
    assert os.path.exists(result)
    assert result.endswith(".png")
    assert "data/raw" in result


def test_ingest_bytes(temp_dir):
    """Test bytes ingestion."""
    test_bytes = b"fake image data"
    result = ingest_from_bytes(test_bytes, "test.png")
    assert os.path.exists(result)
    assert "data/raw" in result
    
    with open(result, "rb") as f:
        assert f.read() == test_bytes


def test_ingest_local_file_not_found():
    """Test ingestion with non-existent file."""
    with pytest.raises(FileNotFoundError):
        ingest_from_local("/nonexistent/file.png")


def test_ingest_local_unsupported_format(temp_dir):
    """Test ingestion with unsupported format."""
    test_file = os.path.join(temp_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("test")
    
    with pytest.raises(ValueError):
        ingest_from_local(test_file)


def test_preprocess(sample_image):
    """Test image preprocessing."""
    result = preprocess(sample_image)
    assert os.path.exists(result)
    assert "data/preprocessed" in result


def test_normalize_date():
    """Test date normalization."""
    # Test various formats
    assert normalize_date("01/15/2024") == "2024-01-15"
    assert normalize_date("2024-01-15") == "2024-01-15"
    assert normalize_date("1/5/2024") == "2024-01-05"
    
    # Test invalid date
    invalid = normalize_date("not a date")
    assert isinstance(invalid, str)


def test_normalize_currency():
    """Test currency normalization."""
    assert normalize_currency("$1,234.56") == 1234.56
    assert normalize_currency("1234.56") == 1234.56
    assert normalize_currency("$1,234") == 1234.0
    assert normalize_currency(1234.56) == 1234.56
    assert normalize_currency("invalid") == 0.0


def test_normalize_invoice_data():
    """Test invoice data normalization."""
    data = {
        "date": "01/15/2024",
        "financial_summary": {
            "subtotal": "$1,000.00",
            "tax": "$100.00",
            "grand_total": "$1,100.00"
        },
        "line_items": [
            {
                "unit_price": "$50.00",
                "line_total": "$100.00",
                "qty": "2"
            }
        ]
    }
    
    normalized = normalize_invoice_data(data)
    
    assert normalized["date"] == "2024-01-15"
    assert normalized["financial_summary"]["subtotal"] == 1000.0
    assert normalized["financial_summary"]["tax"] == 100.0
    assert normalized["financial_summary"]["grand_total"] == 1100.0
    assert normalized["line_items"][0]["unit_price"] == 50.0
    assert normalized["line_items"][0]["line_total"] == 100.0
    assert normalized["line_items"][0]["qty"] == 2.0


def test_check_arithmetic():
    """Test arithmetic validation."""
    # Valid invoice
    valid = {
        "financial_summary": {
            "subtotal": 1000.0,
            "tax": 100.0,
            "grand_total": 1100.0
        },
        "line_items": [
            {"line_total": 500.0},
            {"line_total": 500.0}
        ]
    }
    result = check_arithmetic(valid)
    assert result["ok"] is True
    
    # Invalid invoice (totals don't match)
    invalid = {
        "financial_summary": {
            "subtotal": 1000.0,
            "tax": 100.0,
            "grand_total": 2000.0  # Wrong!
        },
        "line_items": [
            {"line_total": 500.0},
            {"line_total": 500.0}
        ]
    }
    result = check_arithmetic(invalid)
    assert result["ok"] is False
    assert len(result["errors"]) > 0


def test_validate():
    """Test full validation."""
    # Valid invoice
    valid = {
        "invoice_number": "INV-001",
        "financial_summary": {
            "subtotal": 1000.0,
            "tax": 100.0,
            "grand_total": 1100.0
        },
        "line_items": [
            {"line_total": 1000.0}
        ]
    }
    result = validate(valid)
    assert result["ok"] is True
    
    # Invalid invoice (missing required field)
    invalid = {
        "financial_summary": {
            "grand_total": 1100.0
        }
    }
    result = validate(invalid)
    assert result["ok"] is False


def test_generate_id():
    """Test ID generation."""
    id1 = generate_id("inv")
    id2 = generate_id("inv")
    
    assert id1.startswith("inv-")
    assert id2.startswith("inv-")
    assert id1 != id2  # Should be unique


def test_safe_cast():
    """Test safe casting."""
    assert safe_cast("123", int) == 123
    assert safe_cast("123.45", float) == 123.45
    assert safe_cast("invalid", int, default=0) == 0
    assert safe_cast(None, int, default=42) == 42


def test_timestamp():
    """Test timestamp generation."""
    ts = timestamp()
    assert isinstance(ts, str)
    assert "T" in ts or "Z" in ts  # ISO format

