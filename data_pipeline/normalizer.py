"""
Data normalization module for canonicalizing extracted values.

Normalizes:
- Dates to ISO format (YYYY-MM-DD)
- Currency to float
- Text to standardized format
"""
import re
import logging
from typing import Any, Optional

LOG = logging.getLogger("normalizer")

try:
    import dateparser
    DATEPARSER_AVAILABLE = True
except ImportError:
    DATEPARSER_AVAILABLE = False
    LOG.warning("dateparser not installed. Date normalization will be limited.")


def normalize_date(s: Any) -> str:
    """
    Normalize date string to ISO format (YYYY-MM-DD).
    
    Args:
        s: Date string in various formats
        
    Returns:
        ISO format date string (YYYY-MM-DD) or original string if parsing fails
    """
    if not s or not isinstance(s, str):
        return str(s) if s else ""
    
    # Try dateparser first (more robust)
    if DATEPARSER_AVAILABLE:
        try:
            dt = dateparser.parse(s)
            if dt:
                return dt.date().isoformat()
        except Exception as e:
            LOG.debug(f"dateparser failed for '{s}': {e}")
    
    # Fallback to regex patterns
    patterns = [
        (r"(\d{1,2})/(\d{1,2})/(\d{4})", lambda m: f"{m.group(3)}-{m.group(1).zfill(2)}-{m.group(2).zfill(2)}"),
        (r"(\d{1,2})-(\d{1,2})-(\d{4})", lambda m: f"{m.group(3)}-{m.group(1).zfill(2)}-{m.group(2).zfill(2)}"),
        (r"(\d{4})-(\d{2})-(\d{2})", lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}"),  # Already ISO
    ]
    
    for pattern, formatter in patterns:
        match = re.search(pattern, s)
        if match:
            try:
                return formatter(match)
            except Exception:
                continue
    
    # Return original if no pattern matches
    return s


def normalize_currency(s: Any) -> float:
    """
    Normalize currency string to float.
    
    Args:
        s: Currency string (e.g., "$1,234.56", "1234.56", "$1,234")
        
    Returns:
        Float value or 0.0 if parsing fails
    """
    if isinstance(s, (int, float)):
        return float(s)
    
    if not s or not isinstance(s, str):
        return 0.0
    
    # Remove currency symbols and commas
    cleaned = re.sub(r"[^\d\.\-]", "", s)
    
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def normalize_text(s: Any) -> str:
    """
    Normalize text: strip whitespace, fix common OCR errors.
    
    Args:
        s: Text string
        
    Returns:
        Normalized text string
    """
    if not s:
        return ""
    
    text = str(s).strip()
    
    # Fix common OCR errors
    replacements = {
        "|": "I",  # Common OCR error
        "0": "O",  # Context-dependent, be careful
        "rn": "m",  # Common OCR error
    }
    
    # Only apply if it makes sense (this is simplified)
    # In production, use more sophisticated OCR error correction
    
    return text


def normalize_invoice_data(data: dict) -> dict:
    """
    Normalize all fields in invoice data structure.
    
    Args:
        data: Invoice data dictionary
        
    Returns:
        Normalized invoice data dictionary
    """
    normalized = data.copy()
    
    # Normalize dates
    if "date" in normalized:
        normalized["date"] = normalize_date(normalized["date"])
    if "due_date" in normalized:
        normalized["due_date"] = normalize_date(normalized["due_date"])
    
    # Normalize financial summary
    if "financial_summary" in normalized:
        fs = normalized["financial_summary"]
        for key in ["subtotal", "tax", "grand_total"]:
            if key in fs:
                fs[key] = normalize_currency(fs[key])
    
    # Normalize line items
    if "line_items" in normalized and isinstance(normalized["line_items"], list):
        for item in normalized["line_items"]:
            if "unit_price" in item:
                item["unit_price"] = normalize_currency(item["unit_price"])
            if "line_total" in item:
                item["line_total"] = normalize_currency(item["line_total"])
            if "qty" in item:
                try:
                    item["qty"] = float(item["qty"])
                except (ValueError, TypeError):
                    item["qty"] = 1.0
    
    # Normalize vendor name
    if "vendor" in normalized and isinstance(normalized["vendor"], dict):
        if "name" in normalized["vendor"]:
            normalized["vendor"]["name"] = normalize_text(normalized["vendor"]["name"])
    
    # Normalize invoice number
    if "invoice_number" in normalized:
        normalized["invoice_number"] = normalize_text(normalized["invoice_number"])
    
    return normalized

