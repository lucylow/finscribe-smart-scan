# backend/parsers/simple_parser.py
"""Simple parser adapter that wraps existing parsing logic"""
from typing import Dict, Any
import logging

LOG = logging.getLogger("simple_parser")

def parse_basic(ocr_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse OCR result into structured invoice dict.
    
    This is a simple adapter that tries to use existing parsers.
    If the OCR looks like Walmart receipt, use walmart_parser.
    Otherwise, use the invoice_pipeline parser.
    """
    raw_text = ocr_result.get("raw_text", "")
    words = ocr_result.get("words", [])
    
    # Check if it's a Walmart receipt
    if "WALMART" in raw_text.upper() or "WAL-MART" in raw_text.upper():
        try:
            from backend.parsers.walmart_parser import parse_walmart_from_ocr
            return parse_walmart_from_ocr(ocr_result)
        except Exception as e:
            LOG.warning(f"Walmart parser failed: {e}, falling back to generic")
    
    # Use generic invoice pipeline parser
    try:
        from backend.pipeline.invoice_pipeline import parse_regions
        from uuid import uuid4
        structured = parse_regions(ocr_result, uuid4().hex)
        # Convert StructuredInvoice model to dict if needed
        if hasattr(structured, 'dict'):
            return structured.dict()
        elif hasattr(structured, 'model_dump'):
            return structured.model_dump()
        return structured
    except Exception as e:
        LOG.warning(f"Invoice pipeline parser failed: {e}, using minimal parser")
        return _minimal_parse(ocr_result)

def _minimal_parse(ocr_result: Dict[str, Any]) -> Dict[str, Any]:
    """Minimal fallback parser"""
    raw_text = ocr_result.get("raw_text", "")
    words = ocr_result.get("words", [])
    
    return {
        "vendor": {"name": "Unknown Vendor"},
        "invoice_date": None,
        "invoice_number": None,
        "line_items": [],
        "financial_summary": {
            "subtotal": None,
            "tax": None,
            "total": None,
            "currency": "USD"
        },
        "raw_text": raw_text,
        "raw_words": words
    }

