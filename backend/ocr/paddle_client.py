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
    start = time.time()
    
    # Look for a sample OCR JSON close to the image name
    sample_json = Path("examples") / (Path(image_path).stem + "_ocr.json")
    if sample_json.exists():
        try:
            with open(sample_json, "r") as f:
                j = json.load(f)
                j["latency_ms"] = int((time.time() - start) * 1000)
                return j
        except Exception:
            pass

    # fallback deterministic mock: attempt simple Tesseract if installed; else return simple text
    try:
        import pytesseract
        from PIL import Image
        txt = pytesseract.image_to_string(Image.open(image_path))
        return {"raw_text": txt, "words": [], "latency_ms": int((time.time() - start) * 1000)}
    except Exception:
        # final fallback: return a short placeholder
        placeholder = "WALMART SUPERCENTER\n1234 Sample St\nDate 11/15/2023  04:32 PM\nItem A 4.99\nItem B 2.50\nSubtotal 7.49\nTax 0.45\nTotal 7.94\nVisa **** 1234"
        return {"raw_text": placeholder, "words": [], "latency_ms": int((time.time() - start) * 1000)}
