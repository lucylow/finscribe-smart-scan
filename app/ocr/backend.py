"""
OCR backend abstraction layer.
Defines the standard interface for OCR backends and provides a factory function.
"""
import os
import logging
from typing import Dict, List, Tuple, Any, Optional

logger = logging.getLogger(__name__)


class OCRResult(dict):
    """
    Standardized OCR result expected by the rest of the pipeline.
    
    Example:
    {
      "text": "raw text",
      "regions": [
         {"type": "vendor", "bbox": [x,y,w,h], "text": "TechCorp", "confidence": 0.98},
         ...
      ],
      "tables": [ ... ],
      "raw": {...}  # original provider-specific payload
    }
    """
    pass


class OCRBackend:
    """Base class for OCR backend implementations."""
    
    def detect(self, image_bytes: bytes) -> OCRResult:
        """
        Run OCR on image bytes and return OCRResult.
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            OCRResult dictionary with standardized structure
        """
        raise NotImplementedError


def get_backend_from_env() -> OCRBackend:
    """
    Factory function: returns OCR backend instance based on OCR_BACKEND env var.
    
    Supported backends:
    - 'mock': Mock backend for testing/dev
    - 'paddle_local': Local PaddleOCR (requires paddlepaddle)
    - 'paddle_hf': Remote Hugging Face PaddleOCR-VL inference
    
    Returns:
        OCRBackend instance
        
    Raises:
        RuntimeError: If required environment variables are missing
        ImportError: If backend dependencies are not installed
    """
    name = os.getenv("OCR_BACKEND", "mock").lower()
    
    if name == "paddle_local":
        try:
            from .paddle_local import PaddleLocalBackend
            use_gpu = os.getenv("PADDLE_USE_GPU", "false").lower() in ("1", "true", "yes")
            return PaddleLocalBackend(use_gpu=use_gpu)
        except ImportError as e:
            logger.error(f"Failed to import PaddleLocalBackend: {e}")
            logger.warning("Falling back to mock backend. Install paddleocr and paddlepaddle to use paddle_local.")
            from .mock import MockOCRBackend
            return MockOCRBackend()
    
    elif name == "paddle_hf":
        try:
            from .paddle_hf import PaddleHFBackend
            token = os.getenv("HF_TOKEN")
            if not token:
                raise RuntimeError("HF_TOKEN environment variable is required for paddle_hf backend")
            return PaddleHFBackend(token=token)
        except ImportError as e:
            logger.error(f"Failed to import PaddleHFBackend: {e}")
            logger.warning("Falling back to mock backend. Install requests to use paddle_hf.")
            from .mock import MockOCRBackend
            return MockOCRBackend()
        except RuntimeError as e:
            logger.error(f"Configuration error for paddle_hf: {e}")
            logger.warning("Falling back to mock backend.")
            from .mock import MockOCRBackend
            return MockOCRBackend()
    
    else:
        # Default to mock
        from .mock import MockOCRBackend
        return MockOCRBackend()

