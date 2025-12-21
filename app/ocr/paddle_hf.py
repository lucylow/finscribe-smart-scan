"""
Remote Hugging Face PaddleOCR-VL backend for cloud-based OCR processing.
Uses Hugging Face Inference API to avoid heavy local dependencies.
"""
import time
import logging
import base64
import os
from typing import Dict, Any, Optional

from .backend import OCRBackend, OCRResult

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests not available. Install requests to use paddle_hf backend.")


class PaddleHFBackend(OCRBackend):
    """
    Remote Hugging Face PaddleOCR-VL backend using the HF Inference API.
    
    This backend calls a remote Hugging Face model endpoint, avoiding
    the need for heavy local dependencies like paddlepaddle.
    """
    
    def __init__(self, token: str, model_url: Optional[str] = None, timeout: int = 60):
        """
        Initialize Hugging Face PaddleOCR-VL backend.
        
        Args:
            token: Hugging Face API token
            model_url: Optional custom model URL (defaults to PaddleOCR-VL on HF)
            timeout: Request timeout in seconds
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "requests is not installed. Install with: pip install requests"
            )
        
        self.token = token
        self.timeout = timeout
        
        # Default to PaddleOCR-VL on Hugging Face
        # Note: The actual API endpoint may vary - adjust based on available models
        self.model_url = model_url or os.getenv(
            "HF_OCR_URL",
            "https://api-inference.huggingface.co/models/PaddlePaddle/PaddleOCR-VL"
        )
        
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"PaddleHFBackend initialized (url={self.model_url})")
    
    def detect(self, image_bytes: bytes) -> OCRResult:
        """
        Run OCR on image bytes using remote Hugging Face API.
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            OCRResult with standardized structure
        """
        start_time = time.time()
        
        try:
            # Encode image as base64
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Prepare payload
            # Note: HF API format may vary - this is a common pattern
            payload = {
                "inputs": image_b64,
                "parameters": {
                    "return_bboxes": True,
                    "return_text": True
                }
            }
            
            # Make request with retries
            last_exception = None
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        self.model_url,
                        headers=self.headers,
                        json=payload,
                        timeout=self.timeout
                    )
                    
                    response.raise_for_status()
                    result_data = response.json()
                    
                    # Parse response (format may vary based on model)
                    regions = []
                    text_blocks = []
                    tables = []
                    
                    # Try to parse different possible response formats
                    if isinstance(result_data, dict):
                        # Format 1: Direct regions/boxes
                        if "regions" in result_data:
                            for region in result_data["regions"]:
                                regions.append({
                                    "type": region.get("type", "unknown"),
                                    "bbox": region.get("bbox", []),
                                    "text": region.get("text", ""),
                                    "confidence": region.get("score", region.get("confidence", 0.0))
                                })
                                text_blocks.append(region.get("text", ""))
                        
                        # Format 2: Text blocks with boxes
                        elif "text_blocks" in result_data:
                            for block in result_data["text_blocks"]:
                                regions.append({
                                    "type": block.get("type", "unknown"),
                                    "bbox": block.get("box", []),
                                    "text": block.get("text", ""),
                                    "confidence": block.get("confidence", 0.0)
                                })
                                text_blocks.append(block.get("text", ""))
                        
                        # Format 3: OCR result format
                        elif "result" in result_data:
                            ocr_result = result_data["result"]
                            if isinstance(ocr_result, list):
                                for item in ocr_result:
                                    if isinstance(item, dict):
                                        regions.append({
                                            "type": item.get("type", "unknown"),
                                            "bbox": item.get("bbox", item.get("box", [])),
                                            "text": item.get("text", ""),
                                            "confidence": item.get("confidence", item.get("score", 0.0))
                                        })
                                        text_blocks.append(item.get("text", ""))
                        
                        # Format 4: Raw text output (fallback)
                        elif "text" in result_data:
                            text = result_data["text"]
                            text_blocks = [text] if isinstance(text, str) else text
                            regions = [{
                                "type": "unknown",
                                "bbox": [0, 0, 0, 0],
                                "text": text if isinstance(text, str) else "\n".join(text),
                                "confidence": 0.9
                            }]
                    
                    elif isinstance(result_data, list):
                        # List of regions
                        for item in result_data:
                            if isinstance(item, dict):
                                regions.append({
                                    "type": item.get("type", "unknown"),
                                    "bbox": item.get("bbox", item.get("box", [])),
                                    "text": item.get("text", ""),
                                    "confidence": item.get("confidence", item.get("score", 0.0))
                                })
                                text_blocks.append(item.get("text", ""))
                    
                    duration = time.time() - start_time
                    
                    return OCRResult({
                        "text": "\n".join(text_blocks) if text_blocks else "",
                        "regions": regions,
                        "tables": tables,
                        "raw": result_data,
                        "meta": {
                            "backend": "paddle_hf",
                            "duration": duration,
                            "latency_ms": duration * 1000,
                            "model_url": self.model_url
                        }
                    })
                    
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"HF API request failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise
                except Exception as e:
                    logger.error(f"Unexpected error in HF API call: {e}", exc_info=True)
                    raise
            
            # If we get here, all retries failed
            if last_exception:
                raise Exception(f"HF API request failed after {max_retries} attempts: {last_exception}")
            else:
                raise Exception(f"HF API request failed after {max_retries} attempts")
                
        except Exception as e:
            logger.error(f"Hugging Face OCR processing failed: {e}", exc_info=True)
            raise Exception(f"OCR processing failed: {str(e)}")

