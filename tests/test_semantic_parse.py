"""
Tests for semantic invoice parsing.
"""

import json
import pytest
from pathlib import Path
from finscribe.semantic_invoice_parser import (
    parse_invoice_fields,
    reconstruct_table,
    parse_table_to_line_items,
    parse_ocr_artifact_to_structured
)
from finscribe.confidence import aggregate_fields, aggregate_invoice_totals
from finscribe.schemas import infer_doc_type, get_schema_for_doc_type, INVOICE_SCHEMA


@pytest.fixture
def invoice_ocr_fixture():
    """Load invoice OCR fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "invoice_ocr.json"
    with open(fixture_path, "r") as f:
        return json.load(f)


def test_parse_invoice_fields(invoice_ocr_fixture):
    """Test parsing invoice fields from OCR text."""
    regions = invoice_ocr_fixture["regions"]
    lines = [r["text"] for r in regions]
    
    result = parse_invoice_fields(lines)
    
    assert result["invoice_no"] == "INV-1234"
    assert result["date"] == "2024-01-15"
    assert result["total"] == 108.00
    assert result["currency"] == "USD"
    assert "ACME CORPORATION" in result.get("vendor_name", "")


def test_reconstruct_table(invoice_ocr_fixture):
    """Test table reconstruction from OCR regions."""
    regions = invoice_ocr_fixture["regions"]
    
    rows = reconstruct_table(regions)
    
    # Should have multiple rows
    assert len(rows) > 0
    
    # Should have header row
    header_row = rows[0] if rows else []
    assert any("Description" in cell or "Quantity" in cell or "Price" in cell for cell in header_row)


def test_parse_table_to_line_items(invoice_ocr_fixture):
    """Test parsing table rows into line items."""
    regions = invoice_ocr_fixture["regions"]
    
    # Filter to table region (middle rows)
    table_regions = [r for r in regions if 100 < r["bbox"][1] < 200]
    rows = reconstruct_table(table_regions)
    
    line_items = parse_table_to_line_items(rows)
    
    # Should extract at least one line item
    assert len(line_items) > 0
    
    # Check first item
    if line_items:
        first_item = line_items[0]
        assert "description" in first_item
        assert "line_total" in first_item


def test_parse_ocr_artifact_to_structured(invoice_ocr_fixture):
    """Test full parsing of OCR artifact to structured invoice."""
    result = parse_ocr_artifact_to_structured(invoice_ocr_fixture)
    
    # Check required fields
    assert result["invoice_number"] == "INV-1234"
    assert result["financial_summary"]["total"] == 108.00
    assert result["financial_summary"]["currency"] == "USD"
    
    # Check confidence scores
    assert "confidence" in result
    assert result["confidence"]["overall"] > 0


def test_aggregate_fields():
    """Test confidence-weighted field aggregation."""
    fields = [
        {"value": "INV-1234", "confidence": 0.9},
        {"value": "INV-1234", "confidence": 0.85},
        {"value": "INV-5678", "confidence": 0.6},
    ]
    
    best_value, conf = aggregate_fields(fields)
    
    # Should pick the value with highest total confidence
    assert best_value == "INV-1234"
    assert conf > 0.6  # Should be reasonably high


def test_aggregate_invoice_totals(invoice_ocr_fixture):
    """Test invoice total extraction and aggregation."""
    regions = invoice_ocr_fixture["regions"]
    
    total, conf = aggregate_invoice_totals(regions)
    
    assert total == 108.00
    assert conf > 0.8


def test_infer_doc_type():
    """Test document type inference."""
    assert infer_doc_type("Invoice #123") == "invoice"
    assert infer_doc_type("Bank Statement for Account") == "bank_statement"
    assert infer_doc_type("Thank you for your purchase") == "receipt"
    assert infer_doc_type("Generic document") == "generic"


def test_get_schema_for_doc_type():
    """Test schema retrieval."""
    schema = get_schema_for_doc_type("invoice")
    assert schema.doc_type == "invoice"
    assert len(schema.fields) > 0
    
    # Test required fields
    required = schema.get_required_fields()
    assert len(required) > 0
    assert all(f.required for f in required)


# ============================================================================
# Tests for finscribe.semantic_parse_task module
# ============================================================================

from decimal import Decimal
from finscribe.semantic_parse_task import parse_ocr_artifact_to_structured, validate_financials


def make_region(text, x=0, y=0, w=100, h=20, confidence=0.98):
    """
    Helper to synthesize an OCR region entry matching the expected artifact format.
    bbox format [x, y, w, h]
    """
    return {"text": text, "bbox": [x, y, w, h], "confidence": confidence}


def test_parse_simple_invoice_success():
    """
    Simple invoice with invoice number, date, vendor, two line items, subtotal, tax and total.
    Expect parsed invoice_no, date, vendor, 2 line items and successful arithmetic validation.
    """
    regions = []

    # Vendor block (top-left)
    regions.append(make_region("ACME Corporation", x=20, y=10))
    regions.append(make_region("123 Industrial Way", x=20, y=30))
    # Invoice number & date near top
    regions.append(make_region("Invoice #: INV-123", x=1400, y=20))
    regions.append(make_region("Date: 2025-12-20", x=1400, y=40))

    # Line item header (ignore)
    regions.append(make_region("Description", x=100, y=300))
    regions.append(make_region("Qty", x=1200, y=300))
    regions.append(make_region("Price", x=1400, y=300))
    regions.append(make_region("Total", x=1700, y=300))

    # Line item 1
    regions.append(make_region("Widget A", x=100, y=340))
    regions.append(make_region("2", x=1200, y=340))
    regions.append(make_region("$50.00", x=1400, y=340))
    regions.append(make_region("$100.00", x=1700, y=340))

    # Line item 2
    regions.append(make_region("Widget B", x=100, y=380))
    regions.append(make_region("1", x=1200, y=380))
    regions.append(make_region("$30.00", x=1400, y=380))
    regions.append(make_region("$30.00", x=1700, y=380))

    # Subtotal / Tax / Total near bottom-right
    regions.append(make_region("Subtotal", x=1400, y=900))
    regions.append(make_region("$130.00", x=1700, y=900))
    regions.append(make_region("Tax (10%)", x=1400, y=930))
    regions.append(make_region("$13.00", x=1700, y=930))
    regions.append(make_region("Total", x=1400, y=960))
    regions.append(make_region("$143.00", x=1700, y=960))

    ocr_artifact = {
        "job_id": "job-test-1",
        "page_key": "staging/job-test-1/page_0.png",
        "ocr": regions,
    }

    structured = parse_ocr_artifact_to_structured(ocr_artifact)

    assert structured["invoice_no"] == "INV-123"
    assert structured["invoice_date"] == "2025-12-20"
    assert "ACME Corporation" in (structured["vendor"] or "")
    assert len(structured["line_items"]) >= 2
    assert structured["subtotal"] == pytest.approx(130.0, rel=1e-6)
    assert structured["tax"] == pytest.approx(13.0, rel=1e-6)
    assert structured["total"] == pytest.approx(143.0, rel=1e-6)
    assert structured["validation"]["math_ok"] is True
    assert structured["needs_review"] is False


def test_parse_invoice_total_mismatch_flags_review():
    """
    Invoice where declared total does not match subtotal+tax -> should set needs_review and validation errors.
    """
    regions = []

    # Minimal top area
    regions.append(make_region("Vendor XYZ", x=10, y=10))
    regions.append(make_region("Invoice: INV-999", x=1300, y=10))
    regions.append(make_region("2025-11-01", x=1300, y=40))

    # One line item
    regions.append(make_region("Service Fee", x=100, y=200))
    regions.append(make_region("1", x=1200, y=200))
    regions.append(make_region("$100.00", x=1700, y=200))

    regions.append(make_region("Subtotal", x=1400, y=600))
    regions.append(make_region("$100.00", x=1700, y=600))
    regions.append(make_region("Tax", x=1400, y=630))
    regions.append(make_region("$10.00", x=1700, y=630))
    # Declared total intentionally wrong
    regions.append(make_region("Total", x=1400, y=660))
    regions.append(make_region("$50.00", x=1700, y=660))

    ocr_artifact = {
        "job_id": "job-test-2",
        "page_key": "staging/job-test-2/page_0.png",
        "ocr": regions,
    }

    structured = parse_ocr_artifact_to_structured(ocr_artifact)
    assert structured["subtotal"] == pytest.approx(100.0, rel=1e-6)
    assert structured["tax"] == pytest.approx(10.0, rel=1e-6)
    assert structured["total"] == pytest.approx(50.0, rel=1e-6)

    assert structured["validation"]["math_ok"] is False
    assert any(e["code"].startswith("TOTAL") or e["code"].startswith("SUBTOTAL") for e in structured["validation"]["errors"])
    assert structured["needs_review"] is True


def test_validate_financials_edge_cases_empty_lines():
    """
    If no line items, but subtotal and total present, validation uses available numbers without crash.
    """
    structured = {
        "line_items": [],
        "subtotal": 0.0,
        "tax": 0.0,
        "total": 0.0
    }
    res = validate_financials(structured)
    assert isinstance(res, dict)
    assert res["math_ok"] is True

