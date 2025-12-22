# finscribe/ocr_client.py
"""
OCR client abstraction.

Provides:
 - OCRClientBase: interface.
 - MockOCRClient: deterministic mock for local dev/demo.
 - PaddleOCRClient: simple HTTP wrapper to a PaddleOCR-VL inference endpoint.

The PaddleOCRClient expects the endpoint to accept multipart/form-data with
key "image" or a POST with raw bytes depending on your service. Adjust the
request code to match your deployed Paddle OCR server API.
"""

from __future__ import annotations
import io
import json
import logging
import os
from typing import List, Dict, Any, Optional

import requests
from PIL import Image

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOGLEVEL", "INFO"))

# Standard region dict: {"text": "...", "bbox":[x,y,w,h], "confidence":0.98}
Region = Dict[str, Any]


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
    Minimal PaddleOCR client wrapper.

    - endpoint: URL to PaddleOCR HTTP inference service (e.g. local flask/fastapi wrapper)
    - The wrapper expects the server to accept multipart/form-data with `image` field
      or raw bytes at POST /predict. If your server uses a different API, adjust
      `_call_endpoint`.
    """

    def __init__(self, endpoint: Optional[str] = None, timeout: int = 30):
        self.endpoint = endpoint or os.getenv("OCR_ENDPOINT", "http://paddle-ocr:8002/predict")
        self.timeout = int(os.getenv("OCR_TIMEOUT", timeout))
        logger.info("PaddleOCRClient configured for endpoint=%s", self.endpoint)

    def analyze_image(self, image_bytes: bytes) -> List[Region]:
        logger.debug("PaddleOCRClient.analyze_image: %s bytes", len(image_bytes or b""))
        try:
            return self._call_endpoint(image_bytes)
        except Exception as e:
            logger.exception("PaddleOCRClient failed; returning empty list: %s", e)
            return []

    def _call_endpoint(self, image_bytes: bytes) -> List[Region]:
        """
        Default POST as multipart/form-data with key 'image'.
        Expected server response: JSON object with a top-level 'regions' list where each region:
            { "text": "...", "bbox":[x,y,w,h], "confidence":float }
        """
        files = {"image": ("image.jpg", io.BytesIO(image_bytes), "image/jpeg")}
        resp = requests.post(self.endpoint, files=files, timeout=self.timeout)
        resp.raise_for_status()
        payload = resp.json()
        logger.debug("PaddleOCRClient response keys: %s", list(payload.keys()))
        # normalize a few possible response shapes
        if "regions" in payload and isinstance(payload["regions"], list):
            return payload["regions"]
        # sometimes 'predictions' or 'outputs'
        for key in ("predictions", "outputs", "result"):
            if key in payload and isinstance(payload[key], list):
                return payload[key]
        # if server returns a list directly:
        if isinstance(payload, list):
            return payload
        # fallback: attempt best-effort parse
        if isinstance(payload, dict):
            # try to find first list value
            for v in payload.values():
                if isinstance(v, list):
                    return v
        raise ValueError("Unexpected PaddleOCR response shape: %s" % type(payload))


def get_ocr_client() -> OCRClientBase:
    """
    Factory function to get OCR client based on environment variables.
    
    Environment:
        MODEL_MODE=mock -> MockOCRClient
        MODEL_MODE=paddle or OCR_ENDPOINT set -> PaddleOCRClient
    """
    mode = os.getenv("MODEL_MODE", "mock").lower()
    if mode == "mock":
        logger.info("Using MockOCRClient (MODEL_MODE=mock)")
        return MockOCRClient()
    else:
        # Use PaddleOCRClient (HTTP endpoint wrapper)
        endpoint = os.getenv("OCR_ENDPOINT")
        if endpoint:
            logger.info("Using PaddleOCRClient with endpoint=%s", endpoint)
            return PaddleOCRClient(endpoint=endpoint)
        else:
            logger.warning("MODEL_MODE=%s but OCR_ENDPOINT not set, falling back to MockOCRClient", mode)
            return MockOCRClient()
