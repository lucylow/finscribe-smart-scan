# backend/validation/finance_validator.py
"""
Basic financial validation for invoices.

Validates arithmetic consistency:
- sum(line_items.line_total) == subtotal (tolerance 0.05)
- subtotal + tax approx equals total
"""
from decimal import Decimal

def validate_invoice_basic(parsed: dict) -> dict:
    """
    Basic numeric validation:
    - sum(line_items.line_total) == subtotal (tolerance 0.05)
    - subtotal + tax approx equals total
    """
    errors = []
    try:
        subtotal = Decimal(parsed["financial_summary"].get("subtotal") or "0")
        tax = Decimal(parsed["financial_summary"].get("tax") or "0")
        total = Decimal(parsed["financial_summary"].get("total") or "0")
    except Exception:
        return {"ok": False, "errors": ["invalid numeric totals"], "field_confidences": {}}

    # compute line sum
    line_sum = Decimal("0")
    for li in parsed.get("line_items", []):
        try:
            line_sum += Decimal(li.get("line_total") or li.get("unit_price") or "0")
        except Exception:
            pass

    # tolerance
    tol = Decimal("0.05")
    if abs(line_sum - subtotal) > tol:
        errors.append(f"line_items sum {line_sum} != subtotal {subtotal}")

    if abs((subtotal + tax) - total) > tol:
        errors.append(f"subtotal+tax {subtotal+tax} != total {total}")

    return {"ok": len(errors) == 0, "errors": errors, "field_confidences": {}}

