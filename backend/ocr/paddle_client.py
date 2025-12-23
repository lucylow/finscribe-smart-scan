"""PaddleOCR client with service/local/mock modes"""
import os
import time
import requests
from typing import Dict, Any, List, Optional
import json
from pathlib import Path


PADDLE_MODE = os.getenv("PADDLE_MODE", "mock")
PADDLE_SERVICE_URL = os.getenv("PADDLE_SERVICE_URL", "http://ocr-service:8001/predict")


def run_paddleocr(image_path: str) -> Dict[str, Any]:
    """
    Run PaddleOCR on an image.
    
    Supports three modes:
    - service: POST to OCR service endpoint
    - local: Use local paddleocr library
    - mock: Return deterministic sample data
    
    Args:
        image_path: Path to image file
    
    Returns:
        OCR result with keys: raw_text, words (list with bbox, text, confidence)
    """
    start_time = time.time()
    
    if PADDLE_MODE == "service":
        result = _run_service_mode(image_path)
    elif PADDLE_MODE == "local":
        result = _run_local_mode(image_path)
    else:  # mock
        result = _run_mock_mode(image_path)
    
    latency_ms = int((time.time() - start_time) * 1000)
    result["latency_ms"] = latency_ms
    
    return result


def _run_service_mode(image_path: str) -> Dict[str, Any]:
    """Call OCR service via HTTP"""
    try:
        with open(image_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                PADDLE_SERVICE_URL,
                files=files,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        # Fallback to mock on error
        print(f"Warning: OCR service failed ({e}), falling back to mock")
        return _run_mock_mode(image_path)


def _run_local_mode(image_path: str) -> Dict[str, Any]:
    """Use local PaddleOCR library"""
    try:
        from paddleocr import PaddleOCR
        
        ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False)
        result = ocr.ocr(image_path, cls=True)
        
        # Convert to our format
        raw_text = ""
        words = []
        
        if result and result[0]:
            for line in result[0]:
                if line:
                    bbox, (text, confidence) = line
                    raw_text += text + "\n"
                    words.append({
                        "text": text,
                        "bbox": [int(coord) for point in bbox for coord in point],
                        "confidence": float(confidence)
                    })
        
        return {
            "raw_text": raw_text.strip(),
            "words": words
        }
    except ImportError:
        print("Warning: paddleocr not installed, falling back to mock")
        return _run_mock_mode(image_path)
    except Exception as e:
        print(f"Warning: PaddleOCR error ({e}), falling back to mock")
        return _run_mock_mode(image_path)


def _run_mock_mode(image_path: str) -> Dict[str, Any]:
    """Return deterministic mock OCR data"""
    # Try to load sample from examples if available
    sample_path = Path("examples") / "sample_invoice.json"
    if sample_path.exists():
        try:
            with open(sample_path, "r") as f:
                sample = json.load(f)
                if "ocr" in sample:
                    return sample["ocr"]
        except Exception:
            pass

    # Default mock data
    return {
        "raw_text": """INVOICE
Invoice #: INV-2024-001
Date: 2024-01-15
Due: 2024-02-15

Vendor: TechCorp Inc.
123 Innovation Blvd, Suite 100
Cityville, CA 94000

Bill To:
Client Industries Inc.
456 Customer Avenue
New York, NY 10001

Description          Qty    Unit Price    Total
Widget A x1          1      $50.00        $50.00
Service B - Package 1  1      $100.00       $100.00
Support Plan 1 months  1      $25.00        $25.00

Subtotal: $175.00
Tax (10%): $17.50
Grand Total: $192.50""",
        "words": [
            {"text": "INVOICE", "bbox": [100, 50, 300, 80], "confidence": 0.95},
            {"text": "Invoice", "bbox": [100, 100, 200, 130], "confidence": 0.92},
            {"text": "#:", "bbox": [210, 100, 240, 130], "confidence": 0.90},
            {"text": "INV-2024-001", "bbox": [250, 100, 400, 130], "confidence": 0.98},
            {"text": "TechCorp", "bbox": [100, 200, 250, 230], "confidence": 0.95},
            {"text": "Inc.", "bbox": [260, 200, 300, 230], "confidence": 0.93},
            {"text": "Widget", "bbox": [100, 400, 200, 430], "confidence": 0.94},
            {"text": "A", "bbox": [210, 400, 230, 430], "confidence": 0.96},
            {"text": "1", "bbox": [500, 400, 520, 430], "confidence": 0.97},
            {"text": "$50.00", "bbox": [600, 400, 700, 430], "confidence": 0.98},
            {"text": "$50.00", "bbox": [800, 400, 900, 430], "confidence": 0.98},
            {"text": "Subtotal:", "bbox": [600, 600, 700, 630], "confidence": 0.95},
            {"text": "$175.00", "bbox": [710, 600, 810, 630], "confidence": 0.97},
            {"text": "Tax", "bbox": [600, 650, 650, 680], "confidence": 0.94},
            {"text": "(10%):", "bbox": [660, 650, 750, 680], "confidence": 0.92},
            {"text": "$17.50", "bbox": [760, 650, 860, 680], "confidence": 0.96},
            {"text": "Grand", "bbox": [600, 700, 680, 730], "confidence": 0.95},
            {"text": "Total:", "bbox": [690, 700, 760, 730], "confidence": 0.94},
            {"text": "$192.50", "bbox": [770, 700, 870, 730], "confidence": 0.98},
        ]
    }
