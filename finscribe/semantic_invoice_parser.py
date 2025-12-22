"""
Invoice-specific semantic parsing heuristics.

Used as:
- primary rule-based parser
- fallback when ML confidence is low
"""

import re
from typing import Dict, List, Any, Optional, Tuple


INVOICE_NO_RE = re.compile(
    r"(invoice|inv)[\s#:]*([A-Z0-9\-]+)", re.IGNORECASE
)

DATE_RE = re.compile(
    r"(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
)

CURRENCY_RE = re.compile(r"\b(USD|EUR|GBP|CAD|JPY|CNY|AUD|CHF|INR)\b")
AMOUNT_RE = re.compile(r"\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?")

# Additional patterns for better coverage
VENDOR_NAME_RE = re.compile(r"^[A-Z][A-Z0-9\s&\-.,]+(?:INC|LLC|LTD|CORP|CO|COMPANY)", re.IGNORECASE | re.MULTILINE)
TOTAL_RE = re.compile(
    r"(?:total|grand\s+total|amount\s+due|balance\s+due)[\s:]*\$?\s*([\d,]+\.?\d*)",
    re.IGNORECASE
)
SUBTOTAL_RE = re.compile(
    r"subtotal[\s:]*\$?\s*([\d,]+\.?\d*)",
    re.IGNORECASE
)
TAX_RE = re.compile(
    r"(?:tax|sales\s+tax|vat)[\s:]*\$?\s*([\d,]+\.?\d*)",
    re.IGNORECASE
)


def parse_invoice_fields(lines: List[str]) -> Dict[str, Any]:
    """
    Parse invoice fields from text lines using regex patterns.
    
    Args:
        lines: List of text lines from OCR output
        
    Returns:
        Dictionary with parsed invoice fields
    """
    text = " ".join(lines)
    text_lower = text.lower()

    invoice_no = None
    date = None
    due_date = None
    currency = None
    total = None
    subtotal = None
    tax = None
    vendor_name = None

    # Extract invoice number
    if m := INVOICE_NO_RE.search(text):
        invoice_no = m.group(2).strip()

    # Extract dates (first is invoice date, second is due date if present)
    dates = DATE_RE.findall(text)
    if dates:
        date = dates[0]
        if len(dates) > 1:
            due_date = dates[1]

    # Extract currency
    if m := CURRENCY_RE.search(text):
        currency = m.group(1)

    # Extract amounts - collect all potential amounts
    amounts = []
    for match in AMOUNT_RE.finditer(text):
        amount_str = match.group(0).replace("$", "").replace(",", "")
        try:
            amount = float(amount_str)
            if amount > 0:  # Only positive amounts
                amounts.append(amount)
        except ValueError:
            continue

    # Extract specific financial fields using targeted patterns
    if m := TOTAL_RE.search(text):
        try:
            total = float(m.group(1).replace(",", ""))
        except (ValueError, AttributeError):
            pass

    if m := SUBTOTAL_RE.search(text):
        try:
            subtotal = float(m.group(1).replace(",", ""))
        except (ValueError, AttributeError):
            pass

    if m := TAX_RE.search(text):
        try:
            tax = float(m.group(1).replace(",", ""))
        except (ValueError, AttributeError):
            pass

    # If total wasn't found by pattern, use max amount as fallback
    if total is None and amounts:
        total = max(amounts)

    # Extract vendor name (usually in first few lines)
    for line in lines[:15]:  # Check first 15 lines
        line_stripped = line.strip()
        if m := VENDOR_NAME_RE.search(line_stripped):
            vendor_name = m.group(0).strip()
            break
        # Fallback: first substantial line
        if not vendor_name and len(line_stripped) > 3:
            # Skip common headers
            skip_words = ["invoice", "bill to", "ship to", "date", "page", "invoice number"]
            if not any(word in line_stripped.lower() for word in skip_words):
                vendor_name = line_stripped
                break

    return {
        "invoice_no": invoice_no,
        "date": date,
        "due_date": due_date,
        "currency": currency or "USD",  # Default to USD
        "total": total,
        "subtotal": subtotal,
        "tax": tax,
        "vendor_name": vendor_name,
        "all_amounts": sorted(amounts, reverse=True)[:10] if amounts else [],  # Top 10 amounts
    }


def reconstruct_table(regions: List[Dict[str, Any]], row_threshold: int = 12) -> List[List[str]]:
    """
    Simple heuristic for table reconstruction:
    - sort regions by y coordinate
    - cluster rows by y-distance threshold
    
    Args:
        regions: List of OCR regions with 'bbox' and 'text' fields
        row_threshold: Maximum y-distance (in pixels) to consider regions as same row
        
    Returns:
        List of rows, where each row is a list of text strings
    """
    if not regions:
        return []
    
    # Sort by y coordinate (top to bottom)
    sorted_regions = sorted(regions, key=lambda r: r.get("bbox", [0, 0, 0, 0])[1])
    
    rows = []
    current_row = []
    last_y = None
    
    for region in sorted_regions:
        bbox = region.get("bbox", [0, 0, 0, 0])
        if len(bbox) < 2:
            continue
            
        y = bbox[1]  # y coordinate (top edge)
        text = region.get("text", "").strip()
        
        if not text:
            continue
        
        # Check if this region belongs to the current row
        if last_y is None or abs(y - last_y) < row_threshold:
            current_row.append({
                "text": text,
                "bbox": bbox,
                "x": bbox[0]  # Store x for later sorting within row
            })
        else:
            # New row detected - finalize current row
            if current_row:
                # Sort current row by x coordinate (left to right)
                current_row_sorted = sorted(current_row, key=lambda r: r["x"])
                rows.append([r["text"] for r in current_row_sorted])
            current_row = [{
                "text": text,
                "bbox": bbox,
                "x": bbox[0]
            }]
        
        last_y = y
    
    # Don't forget the last row
    if current_row:
        current_row_sorted = sorted(current_row, key=lambda r: r["x"])
        rows.append([r["text"] for r in current_row_sorted])
    
    return rows


def parse_table_to_line_items(table_rows: List[List[str]]) -> List[Dict[str, Any]]:
    """
    Attempt to parse table rows into structured line items.
    
    Args:
        table_rows: List of rows, where each row is a list of cell strings
        
    Returns:
        List of line item dictionaries
    """
    line_items = []
    
    for row in table_rows:
        if len(row) < 2:  # Need at least description and amount
            continue
        
        # Common table formats:
        # [description, qty, unit_price, total]
        # [description, total]
        # [qty, description, unit_price, total]
        
        item = {
            "description": "",
            "quantity": 1.0,
            "unit_price": 0.0,
            "line_total": 0.0
        }
        
        # Try to find description (usually longest non-numeric string)
        descriptions = [cell for cell in row if not re.match(r"^\$?\d+[.,]?\d*$", cell.strip())]
        if descriptions:
            item["description"] = " ".join(descriptions)
        
        # Try to find amounts (numeric values)
        amounts = []
        for cell in row:
            # Remove currency symbols and commas
            cleaned = cell.replace("$", "").replace(",", "").strip()
            try:
                amount = float(cleaned)
                amounts.append(amount)
            except ValueError:
                continue
        
        if amounts:
            # Assume last amount is line total
            item["line_total"] = amounts[-1]
            
            # If multiple amounts, try to infer quantity and unit price
            if len(amounts) >= 2:
                item["quantity"] = amounts[0] if amounts[0] < 1000 else 1.0  # Heuristic: qty usually < 1000
                item["unit_price"] = amounts[-2] if len(amounts) >= 2 else amounts[-1]
            elif len(amounts) == 1:
                item["unit_price"] = amounts[0]
        
        if item["description"]:  # Only add if we have a description
            line_items.append(item)
    
    return line_items


def parse_ocr_artifact_to_structured(ocr_artifact: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point: Parse OCR artifact into structured invoice data.
    
    Args:
        ocr_artifact: OCR output with 'regions' list containing 'text' and 'bbox'
        
    Returns:
        Structured invoice dictionary
    """
    regions = ocr_artifact.get("regions", [])
    
    # Extract text lines from regions
    lines = [r.get("text", "") for r in regions if r.get("text")]
    
    # Parse invoice fields
    fields = parse_invoice_fields(lines)
    
    # Reconstruct table and parse line items
    table_rows = reconstruct_table(regions)
    line_items = parse_table_to_line_items(table_rows)
    
    # Calculate confidence scores (simple heuristic based on field presence)
    confidence = {
        "invoice_no": 0.9 if fields["invoice_no"] else 0.0,
        "date": 0.85 if fields["date"] else 0.0,
        "total": 0.95 if fields["total"] else 0.0,
        "vendor_name": 0.8 if fields["vendor_name"] else 0.0,
        "line_items": 0.7 if line_items else 0.0,
    }
    confidence["overall"] = sum(confidence.values()) / len([v for v in confidence.values() if v > 0]) if any(confidence.values()) else 0.0
    
    return {
        "invoice_number": fields["invoice_no"],
        "invoice_date": fields["date"],
        "due_date": fields["due_date"],
        "vendor": {
            "name": fields["vendor_name"]
        },
        "line_items": line_items,
        "financial_summary": {
            "subtotal": fields["subtotal"],
            "tax": fields["tax"],
            "total": fields["total"],
            "currency": fields["currency"]
        },
        "confidence": confidence,
        "source": "semantic_invoice_parser"
    }

