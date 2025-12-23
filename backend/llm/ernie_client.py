"""ERNIE LLM client for validation"""
import os
import time
import requests
from typing import Dict, Any, Optional
from decimal import Decimal


ERNIE_URL = os.getenv("ERNIE_URL", "")


def call_ernie_validate(structured_invoice: Dict[str, Any], ocr_text: str) -> Dict[str, Any]:
    """
    Call ERNIE service to validate invoice.
    
    Args:
        structured_invoice: Structured invoice data
        ocr_text: Raw OCR text
    
    Returns:
        Validation result with keys: validated_invoice, ok, confidence, errors
    """
    if not ERNIE_URL:
        # No ERNIE URL configured, use mock
        return mock_ernie_response(structured_invoice)
    
    try:
        prompt = _build_validation_prompt(structured_invoice, ocr_text)
        
        response = requests.post(
            ERNIE_URL,
            json={"prompt": prompt, "max_tokens": 1000},
            timeout=15,
            headers={"Content-Type": "application/json"}
        )
        
        # Retry once on failure
        if response.status_code != 200:
            time.sleep(1)
            response = requests.post(
                ERNIE_URL,
                json={"prompt": prompt, "max_tokens": 1000},
                timeout=15,
                headers={"Content-Type": "application/json"}
            )
        
            response.raise_for_status()
        result = response.json()
        
        # Parse response
        validated = result.get("validated_invoice", structured_invoice)
        ok = result.get("ok", True)
        confidence = result.get("confidence", 0.85)
        errors = result.get("errors", [])
        
        return {
            "validated_invoice": validated,
            "ok": ok,
            "confidence": confidence,
            "errors": errors
        }
        
    except Exception as e:
        # Fallback to mock on error
        print(f"Warning: ERNIE validation failed ({e}), using mock")
        return mock_ernie_response(structured_invoice)


def mock_ernie_response(structured_invoice: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock ERNIE response for local demo.
    
    Performs basic arithmetic validation and returns high confidence
    if math checks out, otherwise suggests corrections.
    """
    # Basic arithmetic check
    line_items = structured_invoice.get("line_items", [])
    financial_summary = structured_invoice.get("financial_summary", {})
    
    # Compute expected totals
    computed_subtotal = Decimal("0")
    for item in line_items:
        qty = Decimal(str(item.get("quantity", 0)))
        unit_price = Decimal(str(item.get("unit_price", 0)))
        computed_subtotal += qty * unit_price
    
    subtotal = Decimal(str(financial_summary.get("subtotal", 0)))
    tax_amount = Decimal(str(financial_summary.get("tax_amount", 0)))
    grand_total = Decimal(str(financial_summary.get("grand_total", 0)))
    
    # Check arithmetic
    tolerance = Decimal("0.02")  # 2% tolerance
    subtotal_ok = abs(computed_subtotal - subtotal) / max(abs(subtotal), Decimal("1")) <= tolerance
    
    expected_total = subtotal + tax_amount
    total_ok = abs(expected_total - grand_total) / max(abs(grand_total), Decimal("1")) <= tolerance
    
    ok = subtotal_ok and total_ok
    errors = []
    
    if not subtotal_ok:
        errors.append(f"Subtotal mismatch: computed {computed_subtotal}, found {subtotal}")
    
    if not total_ok:
        errors.append(f"Total mismatch: expected {expected_total}, found {grand_total}")
    
    # Return validated invoice (same as input if OK, with corrections if not)
    validated_invoice = structured_invoice.copy()
    
    if not ok:
        # Suggest corrections
        validated_invoice["financial_summary"] = financial_summary.copy()
        validated_invoice["financial_summary"]["subtotal"] = float(computed_subtotal)
        validated_invoice["financial_summary"]["grand_total"] = float(expected_total)
    
    confidence = 0.95 if ok else 0.65
    
    return {
        "validated_invoice": validated_invoice,
        "ok": ok,
        "confidence": confidence,
        "errors": errors
    }


def _build_validation_prompt(structured_invoice: Dict[str, Any], ocr_text: str) -> str:
    """Build validation prompt for ERNIE"""
    return f"""Validate this invoice data and check for arithmetic errors, missing fields, and inconsistencies.

OCR Text:
{ocr_text[:1000]}

Structured Invoice:
{structured_invoice}

Please validate:
1. Arithmetic: line items sum to subtotal, subtotal + tax = grand total
2. Completeness: all required fields present
3. Consistency: dates are valid, vendor info matches

Return JSON with:
- validated_invoice: corrected invoice if needed
- ok: boolean validation result
- confidence: confidence score 0-1
- errors: list of error messages
"""
