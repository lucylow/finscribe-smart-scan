# backend/parsers/simple_parser.py
import re
from decimal import Decimal
from typing import Dict, Any

_money_re = re.compile(r"([\$]?)([0-9]+(?:[.,][0-9]{1,2})?)")

def _parse_money(s):
    if not s: return None
    m = _money_re.search(s)
    if not m: return None
    token = m.group(2).replace(",", "")
    try:
        return float(token)
    except Exception:
        return None

def parse_basic(ocr_json: Dict[str,Any]) -> Dict[str,Any]:
    raw = ocr_json.get("raw_text","")
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    vendor = lines[0] if lines else "Unknown Vendor"
    subtotal = tax = total = None
    for ln in reversed(lines[-30:]):
        low = ln.lower()
        if "subtotal" in low and subtotal is None:
            subtotal = _parse_money(ln)
        if "tax" in low and tax is None:
            tax = _parse_money(ln)
        if ("total" in low or "amount due" in low) and total is None:
            total = _parse_money(ln)
    items = []
    # crude detection: lines with price at end
    for ln in lines:
        m = re.search(r"^(.*?)[\s]{2,}[\$]?([0-9]+(?:[.,][0-9]{1,2})?)$", ln)
        if m:
            desc = m.group(1).strip()
            price = _parse_money(m.group(2))
            items.append({"description": desc, "quantity": 1, "unit_price": price, "line_total": price})
    return {"vendor": {"name": vendor}, "line_items": items, "financial_summary": {"subtotal": subtotal, "tax": tax, "grand_total": total}, "raw_text": raw}

