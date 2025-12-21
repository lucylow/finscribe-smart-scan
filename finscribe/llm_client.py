"""
LLaMA-Factory API client for validating and correcting OCR-extracted invoice JSON.

Usage:
    from finscribe.llm_client import ask_model_to_validate
    
    ocr_result = {...}  # your OCR -> structured JSON
    corrected = ask_model_to_validate(ocr_result)
    if corrected['validation']['arithmetic_valid'] is False:
        # route to human review
"""
import requests
import json
import re
from typing import Dict, Optional

# Default API configuration
API_URL = "http://localhost:8000/v1/chat/completions"  # or /v1/completions depending on config
HEADERS = {"Content-Type": "application/json"}  # add Authorization if configured

PROMPT_TEMPLATE = """You are a JSON validator for invoice extractions.
Input: {ocr_json}

Task: 
1) Validate arithmetic (subtotal + tax - discount = grand_total). 
2) If arithmetic or fields appear wrong, correct them and return the corrected JSON only. 
3) Add a top-level key "validation":{{"arithmetic_valid": true/false, "notes": "..."}}
Return: only a single JSON object, no explanatory text."""


def ask_model_to_validate(
    ocr_json: Dict, 
    model_name: str = "finscribe-llama",
    api_url: Optional[str] = None,
    headers: Optional[Dict] = None,
    temperature: float = 0.0,
    max_tokens: int = 1024
) -> Dict:
    """
    Send OCR-extracted JSON to LLaMA-Factory API for validation and correction.
    
    Args:
        ocr_json: Dictionary containing OCR-extracted invoice data
        model_name: Name of the model to use (must match LLaMA-Factory config)
        api_url: Override default API URL
        headers: Override default headers (can include Authorization)
        temperature: Sampling temperature (0.0 for deterministic)
        max_tokens: Maximum tokens in response
        
    Returns:
        Corrected JSON dictionary with validation metadata
        
    Raises:
        ValueError: If model response doesn't contain valid JSON
        requests.RequestException: If API request fails
    """
    url = api_url or API_URL
    req_headers = headers or HEADERS
    
    prompt = PROMPT_TEMPLATE.format(ocr_json=json.dumps(ocr_json))
    
    # Chat-style request (adjust if your API expects 'messages' or 'prompt')
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    r = requests.post(url, headers=req_headers, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    
    # Parse returned text (depends on API shape; adapt if using /completions)
    # Example path for chat: data['choices'][0]['message']['content']
    content = None
    if "choices" in data and len(data["choices"]) > 0:
        ch = data["choices"][0]
        if isinstance(ch.get("message"), dict):
            content = ch["message"]["content"]
        else:
            content = ch.get("text") or ch.get("message")
    else:
        content = data.get("output") or str(data)
    
    if not content:
        raise ValueError("Model did not return any content")
    
    # Best-effort: extract first JSON object from response
    match = re.search(r"\{[\s\S]*\}", content)
    if not match:
        raise ValueError(f"Model did not return JSON. Response: {content[:200]}")
    
    corrected_json = json.loads(match.group(0))
    return corrected_json


def validate_arithmetic(invoice_json: Dict) -> bool:
    """
    Helper function to validate arithmetic in invoice JSON.
    
    Checks:
    - Sum of line_items[].line_total == financial_summary.subtotal
    - subtotal + tax_amount - (discount_amount or 0) == grand_total
    
    Args:
        invoice_json: Invoice JSON dictionary
        
    Returns:
        True if arithmetic is valid, False otherwise
    """
    try:
        line_items = invoice_json.get("line_items", [])
        financial = invoice_json.get("financial_summary", {})
        
        # Calculate subtotal from line items
        calculated_subtotal = sum(item.get("line_total", 0) for item in line_items)
        stated_subtotal = financial.get("subtotal", 0)
        
        # Check subtotal matches
        if abs(calculated_subtotal - stated_subtotal) > 0.01:  # allow small floating point errors
            return False
        
        # Calculate grand total
        tax_amount = financial.get("tax_amount", 0)
        discount_amount = financial.get("discount_amount", 0)
        calculated_total = stated_subtotal + tax_amount - discount_amount
        stated_total = financial.get("grand_total", 0)
        
        # Check grand total matches
        if abs(calculated_total - stated_total) > 0.01:
            return False
        
        return True
    except (KeyError, TypeError, ValueError):
        return False


