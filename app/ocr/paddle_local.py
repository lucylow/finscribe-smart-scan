"""
Local PaddleOCR backend for on-premise OCR processing.
Requires paddleocr and paddlepaddle packages.
"""
import time
import logging
import io
from typing import Dict, Any, Optional
import numpy as np

from .backend import OCRBackend, OCRResult

logger = logging.getLogger(__name__)

try:
    from paddleocr import PaddleOCR
    from PIL import Image
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logger.warning("PaddleOCR not available. Install paddleocr and paddlepaddle to use paddle_local backend.")


class PaddleLocalBackend(OCRBackend):
    """
    Local PaddleOCR backend using the PaddleOCR Python package.
    
    This backend runs OCR locally, which is faster for on-premise deployments
    but requires paddlepaddle and paddleocr to be installed.
    """
    
    def __init__(self, lang: str = 'en', use_gpu: bool = False, det_db_box_thresh: float = 0.3):
        """
        Initialize PaddleOCR local backend.
        
        Args:
            lang: Language code (default: 'en')
            use_gpu: Whether to use GPU acceleration
            det_db_box_thresh: Detection threshold for text boxes
        """
        if not PADDLEOCR_AVAILABLE:
            raise ImportError(
                "PaddleOCR is not installed. Install with: "
                "pip install paddleocr paddlepaddle"
            )
        
        try:
            # Initialize PaddleOCR detector + recognizer
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=lang,
                use_gpu=use_gpu,
                det_db_box_thresh=det_db_box_thresh
            )
            logger.info(f"PaddleOCR initialized (lang={lang}, use_gpu={use_gpu})")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise
    
    def detect(self, image_bytes: bytes) -> OCRResult:
        """
        Run OCR on image bytes using local PaddleOCR.
        
        Args:
            image_bytes: Image data as bytes
            
        Returns:
            OCRResult with standardized structure
        """
        start_time = time.time()
        
        try:
            # Convert bytes to PIL Image, then to numpy array
            im = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            im_array = np.array(im)
            
            # Run OCR
            result = self.ocr.ocr(im_array, cls=True)
            
            # Convert PaddleOCR result to OCRResult standard
            regions = []
            text_blocks = []
            
            if result and result[0]:
                for line in result[0]:
                    if not line or len(line) < 2:
                        continue
                    
                    # PaddleOCR returns: [ [[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ('text', confidence) ]
                    box, (txt, conf) = line
                    
                    # Extract bounding box coordinates
                    x_coords = [pt[0] for pt in box]
                    y_coords = [pt[1] for pt in box]
                    x = min(x_coords)
                    y = min(y_coords)
                    w = max(x_coords) - min(x_coords)
                    h = max(y_coords) - min(y_coords)
                    
                    regions.append({
                        "type": "unknown",  # PaddleOCR doesn't provide region type
                        "bbox": [int(x), int(y), int(w), int(h)],
                        "text": txt,
                        "confidence": float(conf)
                    })
                    text_blocks.append(txt)
            
            duration = time.time() - start_time
            
            return OCRResult({
                "text": "\n".join(text_blocks) if text_blocks else "",
                "regions": regions,
                "tables": [],  # PaddleOCR doesn't extract tables by default
                "raw": result,
                "meta": {
                    "backend": "paddle_local",
                    "duration": duration,
                    "latency_ms": duration * 1000
                }
            })
            
        except Exception as e:
            logger.error(f"PaddleOCR processing failed: {e}", exc_info=True)
            raise Exception(f"OCR processing failed: {str(e)}")

