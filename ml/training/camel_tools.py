"""
CAMEL tools - Wraps OCR and validation services as FunctionTools for CAMEL agents.
"""
import os
import json
import requests
from typing import Dict, Any, Optional

# Configuration from environment
OCR_URL = os.getenv("PADDLEOCR_VLLM_URL", "http://localhost:8001/v1")
VALIDATOR_URL = os.getenv("VALIDATOR_URL", "http://localhost:8100/v1/validate")
LLAMA_API_URL = os.getenv("LLAMA_API_URL", "http://localhost:8000/v1/chat/completions")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "finscribe-llama")
TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "60"))

# Headers for LLM API if needed
HEADERS = {"Content-Type": "application/json"}
if os.getenv("LLAMA_API_KEY"):
    HEADERS["Authorization"] = f"Bearer {os.getenv('LLAMA_API_KEY')}"


def call_ocr_file_bytes(file_bytes: bytes, filename: str = "invoice.png") -> Dict[str, Any]:
    """
    Call OCR service with file bytes, return OCR result as dict.
    
    Args:
        file_bytes: Raw file bytes (image/pdf)
        filename: Optional filename for service
        
    Returns:
        Dict with OCR results (text, structured data, etc.)
    """
    try:
        # For PaddleOCR-VL vLLM endpoint, we send base64 or multipart
        # Adjust based on your OCR service API
        files = {"file": (filename, file_bytes)}
        
        # Try OCR endpoint first
        ocr_endpoint = f"{OCR_URL}/ocr" if not OCR_URL.endswith("/ocr") else OCR_URL
        
        response = requests.post(ocr_endpoint, files=files, timeout=TIMEOUT)
        response.raise_for_status()
        
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        # Fallback: return error structure
        return {
            "status": "error",
            "error": str(e),
            "text": "",
            "data": {}
        }


def call_validator(ocr_text: Optional[str] = None, ocr_json: Optional[Dict[str, Any]] = None, doc_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Call validation service to correct/validate OCR output.
    
    Args:
        ocr_text: Raw OCR text (optional)
        ocr_json: Structured OCR JSON (optional)
        doc_id: Document ID for tracking
        
    Returns:
        Dict with corrected JSON structure
    """
    try:
        payload = {
            "doc_id": doc_id,
            "ocr_text": ocr_text,
            "ocr_json": ocr_json
        }
        
        response = requests.post(VALIDATOR_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        
        return response.json()
    except requests.exceptions.RequestException as e:
        # Fallback validation - basic structure
        return {
            "doc_id": doc_id,
            "status": "error",
            "error": str(e),
            "corrected": ocr_json or {}
        }


def llama_validate(ocr_json_str: str) -> str:
    """
    Ask validation LLM model to return corrected JSON.
    Returns JSON string.
    """
    try:
        messages = [
            {"role": "system", "content": "You are an invoice JSON validator. Return only valid JSON."},
            {"role": "user", "content": f"Validate and correct this OCR output. Return corrected JSON only: {ocr_json_str}"}
        ]
        
        payload = {
            "model": LLAMA_MODEL,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 2048
        }
        
        response = requests.post(LLAMA_API_URL, headers=HEADERS, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Extract JSON from response
        import re
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            return json_match.group(0)
        
        # If no JSON found, return wrapped content
        return json.dumps({"raw": content, "original": ocr_json_str})
    except Exception as e:
        # Fallback: return error JSON
        return json.dumps({"error": str(e), "original": ocr_json_str})

