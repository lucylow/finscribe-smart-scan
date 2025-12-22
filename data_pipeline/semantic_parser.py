"""
Semantic parser for extracting structured fields from OCR output.

Uses VLM (Vision-Language Model) with heuristic fallback.
"""
import os
import json
import logging
import requests
import re
from typing import Dict, Any

LOG = logging.getLogger("semantic_parser")

VLM_ENDPOINT = os.getenv("VLM_ENDPOINT", "")
VLM_TIMEOUT = int(os.getenv("VLM_TIMEOUT_SECONDS", "60"))


def call_vlm(ocr_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send OCR JSON to VLM inference service for structured extraction.
    
    Args:
        ocr_json: OCR output dictionary
        
    Returns:
        Structured fields dictionary
    """
    if not VLM_ENDPOINT:
        raise ValueError("VLM_ENDPOINT not configured")
    
    LOG.debug(f"Calling VLM endpoint: {VLM_ENDPOINT}")
    
    try:
        response = requests.post(
            VLM_ENDPOINT,
            json={"ocr": ocr_json},
            timeout=VLM_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        LOG.error(f"VLM request failed: {e}")
        raise


def heuristic_parse(ocr_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback heuristic parser using keyword matching and regex.
    
    Args:
        ocr_json: OCR output dictionary
        
    Returns:
        Structured fields dictionary
    """
    text = ocr_json.get("text", "")
    lines = text.splitlines()
    
    out = {
        "vendor": {},
        "invoice_number": "",
        "date": "",
        "due_date": "",
        "line_items": [],
        "financial_summary": {
            "subtotal": 0.0,
            "tax": 0.0,
            "grand_total": 0.0
        }
    }
    
    # Extract invoice number
    invoice_patterns = [
        r"invoice\s*#?\s*:?\s*([A-Z0-9\-]+)",
        r"inv\s*#?\s*:?\s*([A-Z0-9\-]+)",
        r"invoice\s+number\s*:?\s*([A-Z0-9\-]+)",
    ]
    for line in lines:
        for pattern in invoice_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                out["invoice_number"] = match.group(1).strip()
                break
    
    # Extract dates
    date_patterns = [
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{4}-\d{2}-\d{2})",
    ]
    dates_found = []
    for line in lines:
        for pattern in date_patterns:
            matches = re.findall(pattern, line)
            dates_found.extend(matches)
    if dates_found:
        out["date"] = dates_found[0]
        if len(dates_found) > 1:
            out["due_date"] = dates_found[1]
    
    # Extract totals
    total_patterns = [
        r"total\s*:?\s*\$?\s*([\d,]+\.?\d*)",
        r"grand\s+total\s*:?\s*\$?\s*([\d,]+\.?\d*)",
        r"amount\s+due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
    ]
    for line in lines:
        for pattern in total_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    out["financial_summary"]["grand_total"] = float(amount_str)
                except ValueError:
                    pass
                break
    
    # Extract subtotal
    subtotal_patterns = [
        r"subtotal\s*:?\s*\$?\s*([\d,]+\.?\d*)",
        r"sub\s+total\s*:?\s*\$?\s*([\d,]+\.?\d*)",
    ]
    for line in lines:
        for pattern in subtotal_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    out["financial_summary"]["subtotal"] = float(amount_str)
                except ValueError:
                    pass
                break
    
    # Extract tax
    tax_patterns = [
        r"tax\s*:?\s*\$?\s*([\d,]+\.?\d*)",
        r"sales\s+tax\s*:?\s*\$?\s*([\d,]+\.?\d*)",
    ]
    for line in lines:
        for pattern in tax_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    out["financial_summary"]["tax"] = float(amount_str)
                except ValueError:
                    pass
                break
    
    # Try to extract vendor name (first non-empty line, or company name pattern)
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if line and len(line) > 3:
            # Skip common headers
            if not any(skip in line.lower() for skip in ["invoice", "bill to", "ship to", "date", "page"]):
                out["vendor"]["name"] = line
                break
    
    LOG.debug(f"Heuristic parse extracted: invoice_number={out['invoice_number']}, total={out['financial_summary']['grand_total']}")
    
    return out


def parse(ocr_json: Dict[str, Any], use_vlm: bool = True) -> Dict[str, Any]:
    """
    Parse OCR output to structured fields.
    
    Args:
        ocr_json: OCR output dictionary
        use_vlm: Whether to try VLM first (falls back to heuristic if fails)
        
    Returns:
        Structured fields dictionary
    """
    if use_vlm and VLM_ENDPOINT:
        try:
            result = call_vlm(ocr_json)
            LOG.info("VLM parsing successful")
            return result
        except Exception as e:
            LOG.warning(f"VLM parsing failed, falling back to heuristic: {e}")
            return heuristic_parse(ocr_json)
    else:
        LOG.info("Using heuristic parser (VLM disabled)")
        return heuristic_parse(ocr_json)

