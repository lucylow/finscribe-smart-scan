# backend/validation/finance_validator.py
from decimal import Decimal, InvalidOperation

def _safe_dec(v):
    try:
        return Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError):
        return None

def validate_invoice_basic(parsed: dict) -> dict:
    errors = []
    fs = parsed.get("financial_summary", {}) or {}
    subtotal = _safe_dec(fs.get("subtotal"))
    tax = _safe_dec(fs.get("tax"))
    total = _safe_dec(fs.get("grand_total") or fs.get("total") or 0)
    # sum line items
    line_sum = Decimal("0")
    for li in parsed.get("line_items", []):
        val = _safe_dec(li.get("line_total") or li.get("unit_price") or 0)
        if val is None:
            errors.append(f"invalid line value: {li}")
            continue
        line_sum += val
    tol = Decimal("0.5")  # 50 cents tolerance for demo
    if subtotal is not None and abs(line_sum - subtotal) > tol:
        errors.append(f"line_sum {line_sum} != subtotal {subtotal}")
    if subtotal is not None and tax is not None and total is not None:
        if abs((subtotal + tax) - total) > tol:
            errors.append(f"subtotal+tax {subtotal+tax} != total {total}")
    ok = len(errors) == 0
    return {"ok": ok, "errors": errors}

