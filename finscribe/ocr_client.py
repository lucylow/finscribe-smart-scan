"""
ocr_client.py

OCR client abstraction for FinScribe.

Provides:
- OCRClientBase: abstract interface
- PaddleOCRClient: uses `paddleocr` to perform OCR on image bytes
- MockOCRClient: deterministic outputs for local testing
- get_ocr_client(): factory that chooses impl by OCR_MODE env var

Install dependencies:
    pip install paddleocr opencv-python numpy

Notes:
- PaddleOCR has native CPU/GPU variants; document CPU/GPU install in README.
- If paddleocr is not available and OCR_MODE != "mock", an ImportError is raised with guidance.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import os
import logging

logger = logging.getLogger(__name__)


class OCRClientBase(ABC):
    """Abstract OCR client interface."""

    @abstractmethod
    def analyze_image_bytes(self, image_bytes: bytes) -> List[Dict]:
        """
        Analyze raw image bytes and return a list of detected regions.
        Each region is a dict with at least:
            - text: str
            - bbox: [x, y, w, h]
            - confidence: float
        """
        raise NotImplementedError


class MockOCRClient(OCRClientBase):
    """Simple deterministic OCR client for tests and offline demos."""

    def analyze_image_bytes(self, image_bytes: bytes) -> List[Dict]:
        # deterministic placeholder
        logger.debug("MockOCRClient.analyze_image_bytes called (len=%d)", len(image_bytes))
        return [
            {"text": "ACME CORP", "bbox": [12, 12, 240, 48], "confidence": 0.99},
            {"text": "Invoice # INV-001", "bbox": [300, 20, 220, 36], "confidence": 0.98},
            {"text": "Total: $123.45", "bbox": [300, 700, 180, 40], "confidence": 0.96},
        ]


class PaddleOCRClient(OCRClientBase):
    """
    PaddleOCR client.

    Notes:
        pip install paddleocr opencv-python numpy
        pip install paddlepaddle  # CPU/GPU dependent - see Paddle docs
    """

    def __init__(self, lang: str = "en", use_gpu: Optional[bool] = None):
        self.lang = lang
        if use_gpu is None:
            # allow env override
            use_gpu = os.getenv("OCR_USE_GPU", "0") in ("1", "true", "True")
        self.use_gpu = use_gpu

        try:
            # import here to allow module to be importable in environments without paddleocr
            from paddleocr import PaddleOCR  # type: ignore
            self._ocr = PaddleOCR(use_angle_cls=True, lang=self.lang, use_gpu=self.use_gpu)
            logger.info("Initialized PaddleOCR (lang=%s, use_gpu=%s)", self.lang, self.use_gpu)
        except Exception as e:
            logger.exception("Failed to import/initialize PaddleOCR: %s", e)
            raise ImportError(
                "PaddleOCR import failed. Install paddleocr and paddlepaddle (CPU/GPU wheel). "
                "See README for instructions."
            ) from e

        # lazy imports for image handling
        import numpy as _np  # type: ignore
        import cv2 as _cv2  # type: ignore
        self._np = _np
        self._cv2 = _cv2

    def analyze_image_bytes(self, image_bytes: bytes) -> List[Dict]:
        """Run PaddleOCR on image bytes and return normalized region dicts."""
        img_arr = self._np.frombuffer(image_bytes, dtype=self._np.uint8)
        img = self._cv2.imdecode(img_arr, self._cv2.IMREAD_COLOR)
        if img is None:
            logger.error("Failed to decode image bytes")
            return []

        # results: list of [box, (text, score)]
        results = self._ocr.ocr(img, cls=True)

        out = []
        for item in results:
            try:
                bbox = item[0]  # 4 points
                text, score = item[1][0], float(item[1][1])
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                x, y = min(xs), min(ys)
                w, h = max(xs) - x, max(ys) - y
                out.append({"text": text, "bbox": [int(x), int(y), int(w), int(h)], "confidence": float(score)})
            except Exception:
                logger.exception("Error parsing OCR result item: %s", item)
        return out


# Factory
def get_ocr_client() -> OCRClientBase:
    """
    Factory to return OCR client.

    Environment:
        OCR_MODE=mock | paddle
        OCR_LANG=en (optional)
        OCR_USE_GPU=1|0 (optional)
    """
    mode = os.getenv("OCR_MODE", "paddle").lower()
    lang = os.getenv("OCR_LANG", "en")
    use_gpu_env = os.getenv("OCR_USE_GPU", None)
    use_gpu = None
    if use_gpu_env is not None:
        use_gpu = use_gpu_env in ("1", "true", "True")
    if mode in ("mock", "none"):
        logger.info("Using MockOCRClient because OCR_MODE=%s", mode)
        return MockOCRClient()
    elif mode in ("paddle", "paddleocr"):
        return PaddleOCRClient(lang=lang, use_gpu=use_gpu)
    else:
        raise ValueError(f"Unknown OCR_MODE '{mode}'. Valid: mock, paddle")

