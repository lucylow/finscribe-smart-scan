# finscribe/ocr_client.py
"""
OCR client abstraction with local PaddleOCR support.

Provides:
 - OCRClientBase: interface.
 - MockOCRClient: deterministic mock for local dev/demo.
 - PaddleOCRClient: Direct local PaddleOCR integration (no HTTP endpoint required).

This implementation uses PaddleOCR library directly, making it suitable for
local deployments without external OCR services.
"""

from __future__ import annotations
import io
import logging
import os
import time
from typing import List, Dict, Any, Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOGLEVEL", "INFO"))

# Standard region dict: {"text": "...", "bbox":[x,y,w,h], "confidence":0.98}
Region = Dict[str, Any]

# Try to import PaddleOCR
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logger.warning(
        "PaddleOCR not available. Install with: pip install paddleocr paddlepaddle\n"
        "Using mock client as fallback."
    )


class OCRClientBase:
    """Abstract OCR client interface."""

    def analyze_image(self, image_bytes: bytes) -> List[Region]:
        """
        Analyze image bytes and return a list of regions.

        Each region should be a dict containing:
          - text (str)
          - bbox (list of 4 numbers) [x,y,w,h]
          - confidence (float)
        """
        raise NotImplementedError()


class MockOCRClient(OCRClientBase):
    """Simple deterministic mock OCR client for demos/tests."""

    def analyze_image(self, image_bytes: bytes) -> List[Region]:
        # Very simple fake output; you can extend with heuristics
        # or load fixtures if you prefer more realistic tests.
        logger.debug("MockOCRClient.analyze_image called (len=%d)", len(image_bytes or b""))
        return [
            {"text": "ACME Corporation", "bbox": [20, 10, 400, 40], "confidence": 0.99},
            {"text": "Invoice #: INV-123", "bbox": [1400, 20, 300, 20], "confidence": 0.98},
            {"text": "Date: 2025-12-20", "bbox": [1400, 40, 200, 20], "confidence": 0.98},
            {"text": "Widget A 2 $50.00 $100.00", "bbox": [100, 340, 1600, 30], "confidence": 0.95},
            {"text": "Widget B 1 $30.00 $30.00", "bbox": [100, 380, 1600, 30], "confidence": 0.95},
            {"text": "Subtotal $130.00", "bbox": [1400, 900, 400, 30], "confidence": 0.97},
            {"text": "Tax (10%) $13.00", "bbox": [1400, 930, 400, 30], "confidence": 0.95},
            {"text": "Total $143.00", "bbox": [1400, 960, 400, 30], "confidence": 0.98},
        ]


class PaddleOCRClient(OCRClientBase):
    """
    Local PaddleOCR client using the PaddleOCR library directly.
    
    This client runs OCR locally without requiring an HTTP endpoint.
    """

    def __init__(
        self,
        lang: str = "en",
        use_gpu: bool = False,
        use_angle_cls: bool = True,
        det_db_box_thresh: float = 0.3,
    ):
        """
        Initialize local PaddleOCR client.
        
        Args:
            lang: Language code (default: 'en')
            use_gpu: Whether to use GPU acceleration
            use_angle_cls: Whether to use angle classification
            det_db_box_thresh: Detection threshold for text boxes
        """
        if not PADDLEOCR_AVAILABLE:
            raise ImportError(
                "PaddleOCR is not installed. Install with: "
                "pip install paddleocr paddlepaddle"
            )
        
        # Get config from environment variables
        lang = os.getenv("OCR_LANG", lang)
        use_gpu = os.getenv("OCR_USE_GPU", "0").lower() in ("1", "true", "yes")
        use_angle_cls = os.getenv("OCR_USE_ANGLE_CLS", "1").lower() in ("1", "true", "yes")
        
        try:
            self.ocr = PaddleOCR(
                use_angle_cls=use_angle_cls,
                lang=lang,
                use_gpu=use_gpu,
                det_db_box_thresh=det_db_box_thresh,
                show_log=False,  # Reduce verbosity
            )
            logger.info(
                f"PaddleOCR initialized (lang={lang}, use_gpu={use_gpu}, "
                f"use_angle_cls={use_angle_cls})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise

    def analyze_image(self, image_bytes: bytes) -> List[Region]:
        """
        Run OCR on image bytes using local PaddleOCR.
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            List of regions with text, bbox, and confidence
        """
        logger.debug("PaddleOCRClient.analyze_image: %s bytes", len(image_bytes or b""))
        
        try:
            start_time = time.time()
            
            # Convert bytes to PIL Image, then to numpy array
            im = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            im_array = np.array(im)
            
            # Run OCR
            result = self.ocr.ocr(im_array, cls=True)
            
            # Convert PaddleOCR result to standard region format
            regions: List[Region] = []
            
            if result and result[0]:
                for line in result[0]:
                    if not line or len(line) < 2:
                        continue
                    
                    # PaddleOCR returns: [ [[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ('text', confidence) ]
                    box, (txt, conf) = line
                    
                    # Extract bounding box coordinates (convert from 4 corners to [x, y, w, h])
                    x_coords = [pt[0] for pt in box]
                    y_coords = [pt[1] for pt in box]
                    x = min(x_coords)
                    y = min(y_coords)
                    w = max(x_coords) - min(x_coords)
                    h = max(y_coords) - min(y_coords)
                    
                    regions.append({
                        "text": txt,
                        "bbox": [int(x), int(y), int(w), int(h)],
                        "confidence": float(conf),
                    })
            
            duration = time.time() - start_time
            logger.debug(f"PaddleOCR processed image in {duration:.2f}s, found {len(regions)} regions")
            
            return regions
            
        except Exception as e:
            logger.exception("PaddleOCRClient failed: %s", e)
            # Return empty list instead of raising to allow pipeline to continue
            return []


def get_ocr_client() -> OCRClientBase:
    """
    Factory function to get OCR client based on environment variables.
    
    Environment:
        MODEL_MODE=mock -> MockOCRClient
        MODEL_MODE=paddle -> PaddleOCRClient (local)
        OCR_MODE=mock -> MockOCRClient (alternative env var)
        OCR_MODE=paddle -> PaddleOCRClient (local)
    
    Defaults to MockOCRClient if PaddleOCR is not available.
    """
    # Check both MODEL_MODE and OCR_MODE for flexibility
    mode = os.getenv("MODEL_MODE", os.getenv("OCR_MODE", "mock")).lower()
    
    if mode == "mock":
        logger.info("Using MockOCRClient (MODEL_MODE/OCR_MODE=mock)")
        return MockOCRClient()
    elif mode == "paddle":
        if not PADDLEOCR_AVAILABLE:
            logger.warning(
                "PaddleOCR not available but MODEL_MODE=paddle requested. "
                "Falling back to MockOCRClient. "
                "Install with: pip install paddleocr paddlepaddle"
            )
            return MockOCRClient()
        logger.info("Using PaddleOCRClient (local)")
        return PaddleOCRClient()
    else:
        logger.warning(
            f"Unknown OCR mode: {mode}. Supported: mock, paddle. "
            "Falling back to MockOCRClient"
        )
        return MockOCRClient()
