"""
Abstract OCR Provider Interface.

This interface allows for easy integration of different OCR providers
(e.g., PaddleOCR-VL, commercial OCR APIs, alternative models).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class OCRResult(BaseModel):
    """Standard OCR result structure."""
    
    text: str
    tokens: List[Dict[str, Any]]  # List of text tokens with bounding boxes
    bboxes: List[List[int]]  # Bounding boxes [x1, y1, x2, y2]
    layout: Optional[Dict[str, Any]] = None  # Document layout information
    confidence_scores: Optional[Dict[str, float]] = None
    model_version: str
    processing_time_ms: Optional[float] = None


class AbstractOCRProvider(ABC):
    """
    Abstract base class for OCR providers.
    
    Implementations should provide:
    - PaddleOCR-VL integration
    - Commercial OCR API integration
    - Alternative OCR models
    """
    
    @abstractmethod
    async def parse_document(self, file_content: bytes) -> OCRResult:
        """
        Parse a document and extract text with bounding boxes.
        
        Args:
            file_content: Raw document bytes
        
        Returns:
            OCRResult with text, tokens, and bounding boxes
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this OCR provider."""
        pass
    
    @abstractmethod
    def get_model_version(self) -> str:
        """Get the model version being used."""
        pass
    
    def is_available(self) -> bool:
        """
        Check if the OCR provider is available.
        
        Returns:
            True if available, False otherwise
        """
        return True

