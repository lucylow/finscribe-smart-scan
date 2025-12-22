"""
Interface abstractions for model providers.

These interfaces allow for easy swapping of OCR and LLM providers
without modifying core orchestration logic.
"""

from .ocr_provider import AbstractOCRProvider, OCRResult
from .llm_extractor import AbstractLLMExtractor, ExtractionResult

__all__ = [
    "AbstractOCRProvider",
    "OCRResult",
    "AbstractLLMExtractor",
    "ExtractionResult",
]

