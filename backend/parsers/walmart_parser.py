# backend/parsers/walmart_parser.py
"""
Walmart receipt parser.

Parses OCR output from Walmart receipts and extracts structured invoice data.
"""
from typing import List, Dict, Any
from decimal import Decimal, InvalidOperation
import re
from datetime import datetime

CURRENCY_RE = re.compile(r"[\$]?([0-9\.,]+)")

def _parse_money(s: str) -> Decimal:
    if s is None:
        return Decimal("0.00")
    m = CURRENCY_RE.search(s)
    if not m:
        raise ValueError(f"Cannot parse money from: {s!r}")
    token = m.group(1).replace(",", "")
    try:
        return Decimal(token)
    except InvalidOperation:
        return Decimal("0.00")

def _find_first(regex_list, text):
    for r in regex_list:
        m = re.search(r, text, re.IGNORECASE)
        if m:
            return m
    return None

def parse_walmart_from_ocr(ocr_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse OCR output text from a Walmart receipt and produce structured invoice dict.

    Input: ocr_json expected to contain at least 'raw_text' (str) and optional 'words' list.
    Output: {
        vendor: {name, store_number?},
        invoice_date: ISO date string,
        invoice_time: time string,
        line_items: [{description, qty, unit_price, line_total}],
        financial_summary: {subtotal, tax, total},
        payment: {method, last4?}
    }
    """
    raw = ocr_json.get("raw_text") or ""
    words = ocr_json.get("words") or []

    text = raw.replace("\r", "\n")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    result = {
        "vendor": {"name": None, "store_number": None},
        "invoice_date": None,
        "invoice_time": None,
        "line_items": [],
        "financial_summary": {"subtotal": None, "tax": None, "total": None},
        "payment": {"method": None, "last4": None},
        "raw_lines": lines
    }

    # vendor name: first line usually contains WALMART or WALMART SUPERCENTER
    for ln in lines[:6]:
        if re.search(r"\bWALMART\b", ln, re.IGNORECASE):
            result["vendor"]["name"] = ln
            break
    if not result["vendor"]["name"]:
        # fallback to line 0
        result["vendor"]["name"] = lines[0] if lines else "Walmart? (unknown)"

    # attempt to find store number e.g., "Store # 1234"
    m = _find_first([r"Store\s*#\s*(\d+)", r"STORE\s*#\s*(\d+)", r"ST#\s*(\d+)"], text)
    if m:
        result["vendor"]["store_number"] = m.group(1)

    # date/time heuristics: look for common formats
    # examples: 11/15/23  04:32 PM  OR Nov 15, 2023 04:32
    date_time_regexes = [
        r"(\d{1,2}/\d{1,2}/\d{2,4})\s+(\d{1,2}:\d{2}\s*(AM|PM|am|pm)?)",
        r"([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})\s+(\d{1,2}:\d{2}\s*(AM|PM|am|pm)?)",
        r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})"
    ]
    dt_match = _find_first(date_time_regexes, text)
    if dt_match:
        try:
            date_str = dt_match.group(1)
            time_str = dt_match.group(2)
            # normalize date - try multiple parse patterns
            parsed_date = None
            for fmt in ("%m/%d/%Y", "%m/%d/%y", "%b %d, %Y", "%Y-%m-%d"):
                try:
                    parsed_date = datetime.strptime(date_str, fmt).date()
                    break
                except Exception:
                    continue
            if parsed_date is None:
                # try year expansion for yy
                if re.match(r"\d{1,2}/\d{1,2}/\d{2}$", date_str):
                    parsed_date = datetime.strptime(date_str, "%m/%d/%y").date()
            result["invoice_date"] = parsed_date.isoformat() if parsed_date else date_str
            result["invoice_time"] = time_str
        except Exception:
            result["invoice_date"] = date_str
            result["invoice_time"] = time_str

    # financial totals: look for lines with "Subtotal", "Tax", "TOTAL"
    subtotal, tax, total = None, None, None
    for ln in reversed(lines[-20:]):  # totals are usually near the bottom
        lnl = ln.lower()
        if "subtotal" in lnl and subtotal is None:
            subtotal = _parse_money(ln)
            continue
        if re.search(r"\b(tax|sales tax)\b", lnl) and tax is None:
            tax = _parse_money(ln)
            continue
        # total: often "Total" or "AMOUNT DUE" or "Grand Total"
        if re.search(r"\b(total|amount due|amt due|grand total)\b", lnl) and total is None:
            total = _parse_money(ln)
            continue
    result["financial_summary"]["subtotal"] = str(subtotal) if subtotal is not None else None
    result["financial_summary"]["tax"] = str(tax) if tax is not None else None
    result["financial_summary"]["total"] = str(total) if total is not None else None

    # Payment method: look for last lines like "Visa **** 1234" or "CASH"
    for ln in reversed(lines[-10:]):
        if re.search(r"\b(visa|mastercard|amex|discover)\b", ln, re.IGNORECASE):
            # extract last 4 digits
            m = re.search(r"(\d{4})\b", ln)
            result["payment"]["method"] = re.search(r"\b(visa|mastercard|amex|discover)\b", ln, re.IGNORECASE).group(1).upper()
            result["payment"]["last4"] = m.group(1) if m else None
            break
        if re.search(r"\bCASH\b", ln, re.IGNORECASE):
            result["payment"]["method"] = "CASH"
            break

    # Attempt to parse line items: simple heuristic:
    # find the candidate block where lines contain an amount at end
    item_lines = []
    amount_line_re = re.compile(r"([0-9]+\s*[0-9\.,]*\d)\s*$")
    # more robust: find lines that have a price token
    for ln in lines:
        if re.search(r"[\$]?\d+[.,]?\d{0,2}\s*$", ln):
            item_lines.append(ln)

    # Now try to distinguish totals from items: ignore lines that include "subtotal" "tax" "total"
    candidate_items = []
    for ln in item_lines:
        if re.search(r"\b(subtotal|tax|total|change|cash|tender)\b", ln, re.IGNORECASE):
            continue
        candidate_items.append(ln)

    # Parse candidate item lines: description (front) and price at end
    for ln in candidate_items:
        # try to split by two or more spaces or by last space before price
        m = re.search(r"^(.*?)(?:\s{2,}|\s)([\$]?[0-9\.,]+\b)$", ln)
        if not m:
            # fallback: last token maybe price
            parts = ln.rsplit(" ", 1)
            if len(parts) == 2 and re.search(r"[\d\.,]", parts[1]):
                desc, price = parts
            else:
                continue
        else:
            desc, price = m.group(1).strip(), m.group(2).strip()
        # price -> Decimal
        try:
            price_val = _parse_money(price)
        except Exception:
            price_val = Decimal("0.00")
        # No qty parsing on receipts generally; set qty=1 and unit_price=price
        candidate = {
            "description": desc,
            "quantity": 1,
            "unit_price": str(price_val),
            "line_total": str(price_val)
        }
        result["line_items"].append(candidate)

    # de-duplicate items heuristics: if many similar lines or if none, leave empty
    if not result["line_items"]:
        # fallback: parse any lines that look like "XXX  4.99"
        for ln in lines:
            m = re.search(r"^(.{3,50}?)\s+([\$]?[0-9\.,]+\b)\s*$", ln)
            if m:
                desc, price = m.group(1).strip(), m.group(2).strip()
                result["line_items"].append({
                    "description": desc,
                    "quantity": 1,
                    "unit_price": str(_parse_money(price)),
                    "line_total": str(_parse_money(price))
                })

    # Final cleanup: ensure totals as strings or None
    for k in ["subtotal", "tax", "total"]:
        if result["financial_summary"].get(k) is None:
            result["financial_summary"][k] = None

    return result

