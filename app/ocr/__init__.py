"""
OCR backend abstraction module.
Provides a unified interface for different OCR backends (mock, PaddleOCR local, Hugging Face).
"""

from .backend import OCRBackend, OCRResult, get_backend_from_env

__all__ = ["OCRBackend", "OCRResult", "get_backend_from_env"]

