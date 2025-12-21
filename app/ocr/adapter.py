"""
Adapter to bridge the new OCR backend abstraction with existing async interfaces.
"""
import asyncio
import logging
from typing import Dict, Any, Optional

from .backend import OCRBackend, get_backend_from_env
from .utils import with_retries

logger = logging.getLogger(__name__)


class OCRBackendAdapter:
    """
    Adapter that wraps the new OCR backend abstraction to work with
    existing async interfaces and the PaddleOCRVLService structure.
    """
    
    def __init__(self, backend: Optional[OCRBackend] = None):
        """
        Initialize adapter with an OCR backend.
        
        Args:
            backend: OCRBackend instance. If None, uses get_backend_from_env()
        """
        self.backend = backend or get_backend_from_env()
        logger.info(f"OCRBackendAdapter initialized with backend: {type(self.backend).__name__}")
    
    async def analyze_image(
        self,
        image_bytes: bytes,
        region_type: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze image using the OCR backend (async wrapper).
        
        This method adapts the synchronous detect() method to async
        and converts OCRResult to the format expected by existing code.
        
        Args:
            image_bytes: Image data to process
            region_type: Optional region type (for compatibility, not used by all backends)
            prompt: Optional prompt (for compatibility, not used by all backends)
            
        Returns:
            Dict with OCR results in the format expected by existing code
        """
        try:
            # Run OCR in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: with_retries(
                    lambda: self.backend.detect(image_bytes),
                    retries=3,
                    backoff=2
                )
            )
            
            # Convert OCRResult to the format expected by existing code
            # This maintains backward compatibility
            return self._convert_to_legacy_format(result, region_type)
            
        except Exception as e:
            logger.error(f"OCR backend adapter failed: {e}", exc_info=True)
            raise
    
    def _convert_to_legacy_format(
        self,
        result: Dict[str, Any],
        region_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert OCRResult to the format expected by existing PaddleOCRVLService.
        
        Args:
            result: OCRResult dictionary
            region_type: Optional region type
            
        Returns:
            Dict in legacy format
        """
        # Extract data from OCRResult
        text = result.get("text", "")
        regions = result.get("regions", [])
        tables = result.get("tables", [])
        raw = result.get("raw", {})
        meta = result.get("meta", {})
        
        # Convert regions to tokens and bboxes format (legacy)
        tokens = []
        bboxes = []
        
        for region in regions:
            text_val = region.get("text", "")
            if text_val:
                tokens.append({
                    "text": text_val,
                    "confidence": region.get("confidence", 0.0)
                })
            
            bbox = region.get("bbox", [])
            if len(bbox) >= 4:
                bboxes.append({
                    "x": bbox[0],
                    "y": bbox[1],
                    "w": bbox[2],
                    "h": bbox[3],
                    "region_type": region.get("type", "unknown"),
                    "page_index": region.get("page_index", 0)
                })
        
        # Build legacy format
        legacy_result = {
            "status": "success",
            "model_version": f"{meta.get('backend', 'unknown')}-backend",
            "tokens": tokens,
            "bboxes": bboxes,
            "regions": [
                {
                    "type": r.get("type", "unknown"),
                    "content": r.get("text", "")
                }
                for r in regions
            ],
            "latency_ms": meta.get("latency_ms", 0),
            "models_used": [meta.get("backend", "unknown")]
        }
        
        # Add region_type if provided
        if region_type:
            legacy_result["region_type"] = region_type
        
        # Merge in raw data for compatibility
        if raw:
            legacy_result["raw_ocr"] = raw
        
        return legacy_result

