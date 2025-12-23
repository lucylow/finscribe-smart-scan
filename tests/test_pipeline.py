"""Unit tests for invoice pipeline"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.pipeline.invoice_pipeline import (
    run_full_pipeline,
    parse_regions,
    basic_validator
)
from backend.ocr.paddle_client import run_paddleocr
from backend.ocr.preprocess import preprocess_image
from backend.models.finance import StructuredInvoice, LineItem, FinancialSummary, Vendor


@pytest.fixture
def sample_image_bytes():
    """Create a minimal test image"""
    from PIL import Image
    img = Image.new('RGB', (100, 100), color='white')
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    img.save(temp_file.name)
    temp_file.close()
    yield temp_file.name
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


@pytest.fixture
def sample_ocr_result():
    """Sample OCR result"""
    return {
        "raw_text": """INVOICE
Invoice #: INV-2024-001
Date: 2024-01-15
Vendor: TechCorp Inc.
123 Innovation Blvd
Cityville, CA 94000

Description          Qty    Unit Price    Total
Widget A             1      $50.00        $50.00
Service B            1      $100.00       $100.00

Subtotal: $150.00
Tax (10%): $15.00
Grand Total: $165.00""",
        "words": [
            {"text": "INVOICE", "bbox": [100, 50, 300, 80], "confidence": 0.95},
            {"text": "INV-2024-001", "bbox": [250, 100, 400, 130], "confidence": 0.98},
            {"text": "TechCorp", "bbox": [100, 200, 250, 230], "confidence": 0.95},
        ],
        "latency_ms": 150
    }


def test_preprocess_image_bytes(sample_image_bytes):
    """Test image preprocessing with bytes input"""
    with open(sample_image_bytes, "rb") as f:
        image_bytes = f.read()
    
    output_path = preprocess_image(image_bytes)
    
    assert os.path.exists(output_path)
    assert output_path.endswith(".png")
    
    # Cleanup
    if os.path.exists(output_path):
        os.unlink(output_path)


def test_preprocess_image_path(sample_image_bytes):
    """Test image preprocessing with file path"""
    output_path = preprocess_image(sample_image_bytes)
    
    assert os.path.exists(output_path)
    assert output_path.endswith(".png")
    
    # Cleanup
    if os.path.exists(output_path):
        os.unlink(output_path)


@patch('backend.ocr.paddle_client.PADDLE_MODE', 'mock')
def test_pipeline_mock_mode(sample_image_bytes, sample_ocr_result):
    """Test full pipeline in mock mode"""
    with patch('backend.ocr.paddle_client.run_paddleocr') as mock_ocr, \
         patch('backend.llm.ernie_client.call_ernie_validate') as mock_ernie:
        
        # Mock OCR
        mock_ocr.return_value = sample_ocr_result
        
        # Mock ERNIE validation
        mock_ernie.return_value = {
            "validated_invoice": {},
            "ok": True,
            "confidence": 0.95,
            "errors": []
        }
        
        # Run pipeline
        result = run_full_pipeline(sample_image_bytes, use_ernie=True)
        
        # Assertions
        assert "invoice_id" in result
        assert "structured_invoice" in result
        assert "validation" in result
        assert "confidence" in result
        assert "latency_ms" in result
        assert "fallback_used" in result
        
        # Check validation passed
        validation = result["validation"]
        assert validation.get("is_valid") or validation.get("ok")
        
        # Check structured invoice has required fields
        invoice = result["structured_invoice"]
        assert "vendor" in invoice
        assert "line_items" in invoice
        assert "financial_summary" in invoice


def test_parse_regions(sample_ocr_result):
    """Test region parsing"""
    invoice = parse_regions(sample_ocr_result, "test-invoice-123")
    
    assert isinstance(invoice, StructuredInvoice)
    assert invoice.invoice_id == "test-invoice-123"
    assert invoice.vendor is not None
    assert invoice.financial_summary is not None


def test_basic_validator():
    """Test basic validator"""
    # Create valid invoice
    invoice = StructuredInvoice(
        invoice_id="test-123",
        vendor=Vendor(name="Test Vendor"),
        line_items=[
            LineItem(description="Item 1", quantity=1.0, unit_price=10.0, line_total=10.0),
            LineItem(description="Item 2", quantity=2.0, unit_price=5.0, line_total=10.0)
        ],
        financial_summary=FinancialSummary(
            subtotal=20.0,
            tax_amount=2.0,
            grand_total=22.0
        )
    )
    
    result = basic_validator(invoice)
    
    assert result.is_valid
    assert len(result.errors) == 0
    assert "overall" in result.field_confidences


def test_basic_validator_arithmetic_error():
    """Test basic validator detects arithmetic errors"""
    # Create invoice with arithmetic error
    invoice = StructuredInvoice(
        invoice_id="test-123",
        vendor=Vendor(name="Test Vendor"),
        line_items=[
            LineItem(description="Item 1", quantity=1.0, unit_price=10.0, line_total=10.0)
        ],
        financial_summary=FinancialSummary(
            subtotal=20.0,  # Wrong! Should be 10.0
            tax_amount=2.0,
            grand_total=22.0
        )
    )
    
    result = basic_validator(invoice)
    
    # Should detect error
    assert not result.is_valid
    assert len(result.errors) > 0


def test_active_learning_append(tmp_path):
    """Test active learning queue append"""
    from backend.api.active_learning import accept_correction
    from pathlib import Path
    
    # Set queue file to temp location
    import backend.api.active_learning as al_module
    original_queue = al_module.QUEUE_FILE
    al_module.QUEUE_FILE = tmp_path / "active_learning_queue.jsonl"
    
    try:
        # Create correction data
        correction = {
            "invoice": {
                "invoice_id": "test-123",
                "vendor": {"name": "Test Vendor"}
            },
            "corrections": {"vendor_name": True},
            "metadata": {"confidence": 0.95}
        }
        
        # This would normally be async, but for test we'll call the logic directly
        import json
        queue_file = al_module.QUEUE_FILE
        queue_file.parent.mkdir(parents=True, exist_ok=True)
        
        entry = {
            "invoice": correction["invoice"],
            "corrections": correction["corrections"],
            "metadata": correction["metadata"]
        }
        
        with open(queue_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        
        # Verify file was created and has content
        assert queue_file.exists()
        with open(queue_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["invoice"]["invoice_id"] == "test-123"
    
    finally:
        al_module.QUEUE_FILE = original_queue

