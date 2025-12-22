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

