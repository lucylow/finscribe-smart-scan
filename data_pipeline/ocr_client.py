"""
Multi-backend OCR client abstraction.

Supports:
- Local OCR service (PaddleOCR, etc.)
- HuggingFace Inference API
- External HTTP endpoints
"""
import os
import requests
import logging
from typing import Dict, Any

LOG = logging.getLogger("ocr_client")

BACKEND = os.getenv("OCR_BACKEND", "local")
LOCAL_ENDPOINT = os.getenv("OCR_LOCAL_ENDPOINT", "http://localhost:8001/api/ocr")
HF_OCR_ENDPOINT = os.getenv("HF_OCR_ENDPOINT", "")
TIMEOUT = int(os.getenv("OCR_TIMEOUT_SECONDS", "60"))


def call_local_ocr(path: str) -> Dict[str, Any]:
    """
    Call local OCR service endpoint.
    
    Args:
        path: Path to image file
        
    Returns:
        OCR results as dictionary
    """
    LOG.debug(f"Calling local OCR at {LOCAL_ENDPOINT}")
    
    with open(path, "rb") as f:
        files = {"file": (os.path.basename(path), f, "image/png")}
        response = requests.post(
            LOCAL_ENDPOINT,
            files=files,
            timeout=TIMEOUT
        )
    
    response.raise_for_status()
    return response.json()


def call_hf_ocr(path: str) -> Dict[str, Any]:
    """
    Call HuggingFace OCR inference API.
    
    Args:
        path: Path to image file
        
    Returns:
        OCR results as dictionary
    """
    if not HF_OCR_ENDPOINT:
        raise ValueError("HF_OCR_ENDPOINT not configured")
    
    LOG.debug(f"Calling HuggingFace OCR at {HF_OCR_ENDPOINT}")
    
    hf_token = os.getenv("HF_TOKEN", "")
    headers = {}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"
    
    with open(path, "rb") as f:
        files = {"file": (os.path.basename(path), f, "image/png")}
        response = requests.post(
            HF_OCR_ENDPOINT,
            files=files,
            headers=headers,
            timeout=TIMEOUT
        )
    
    response.raise_for_status()
    return response.json()


def call_paddleocr_direct(path: str) -> Dict[str, Any]:
    """
    Call PaddleOCR directly (if installed).
    
    Args:
        path: Path to image file
        
    Returns:
        OCR results as dictionary
    """
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        raise ImportError("PaddleOCR not installed. Install with: pip install paddleocr")
    
    LOG.debug("Using PaddleOCR directly")
    
    ocr = PaddleOCR(use_angle_cls=True, lang='en')
    result = ocr.ocr(path, cls=True)
    
    # Convert to standard format
    text_lines = []
    for line in result[0] if result else []:
        if line:
            text_lines.append({
                "text": line[1][0],
                "confidence": line[1][1],
                "bbox": line[0]
            })
    
    full_text = "\n".join([line["text"] for line in text_lines])
    
    return {
        "text": full_text,
        "lines": text_lines,
        "confidence": sum([l["confidence"] for l in text_lines]) / len(text_lines) if text_lines else 0.0
    }


def run_ocr(path: str) -> Dict[str, Any]:
    """
    Run OCR on image using configured backend.
    
    Args:
        path: Path to image file
        
    Returns:
        OCR results dictionary with 'text', 'lines', 'confidence', etc.
        
    Raises:
        RuntimeError: If backend is not supported or OCR fails
    """
    LOG.info(f"Running OCR on {path} via backend: {BACKEND}")
    
    try:
        if BACKEND == "local":
            return call_local_ocr(path)
        elif BACKEND == "hf":
            return call_hf_ocr(path)
        elif BACKEND == "paddleocr_direct":
            return call_paddleocr_direct(path)
        else:
            raise RuntimeError(f"Unsupported OCR_BACKEND: {BACKEND}. Supported: local, hf, paddleocr_direct")
    except requests.exceptions.RequestException as e:
        LOG.error(f"OCR request failed: {e}")
        raise RuntimeError(f"OCR service unavailable: {e}")
    except Exception as e:
        LOG.error(f"OCR processing failed: {e}", exc_info=True)
        raise

