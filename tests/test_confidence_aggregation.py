"""
Tests for confidence-weighted aggregation.
"""

import pytest
from finscribe.confidence import (
    aggregate_fields,
    aggregate_invoice_totals,
    aggregate_field_candidates
)


def test_aggregate_fields_single():
    """Test aggregation with single candidate."""
    fields = [{"value": "TEST", "confidence": 0.9}]
    value, conf = aggregate_fields(fields)
    
    assert value == "TEST"
    assert conf == 0.9


def test_aggregate_fields_multiple_agree():
    """Test aggregation when multiple sources agree."""
    fields = [
        {"value": "INV-001", "confidence": 0.9},
        {"value": "INV-001", "confidence": 0.85},
        {"value": "INV-001", "confidence": 0.8},
    ]
    
    value, conf = aggregate_fields(fields)
    
    assert value == "INV-001"
    # Confidence should be boosted by agreement
    assert conf > 0.8


def test_aggregate_fields_conflict():
    """Test aggregation when sources conflict."""
    fields = [
        {"value": "INV-001", "confidence": 0.9},
        {"value": "INV-002", "confidence": 0.6},
    ]
    
    value, conf = aggregate_fields(fields)
    
    # Should pick higher confidence value
    assert value == "INV-001"
    assert conf > 0.6


def test_aggregate_field_candidates_text():
    """Test text field candidate aggregation."""
    candidates = [
        {"value": "ACME Corp", "confidence": 0.95},
        {"value": "ACME Corp", "confidence": 0.9},
    ]
    
    result = aggregate_field_candidates("vendor_name", candidates, field_type="text")
    
    assert result["value"] == "ACME Corp"
    assert result["confidence"] > 0.9
    assert result["source_count"] == 2


def test_aggregate_field_candidates_number():
    """Test numeric field candidate aggregation."""
    candidates = [
        {"value": "$100.50", "confidence": 0.9},
        {"value": "100.50", "confidence": 0.85},
        {"value": 100.5, "confidence": 0.95},
    ]
    
    result = aggregate_field_candidates("total", candidates, field_type="number")
    
    assert result["value"] == 100.5
    assert result["confidence"] > 0.85
    assert result["field_type"] == "number"

