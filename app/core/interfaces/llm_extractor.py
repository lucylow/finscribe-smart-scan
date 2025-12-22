"""
Abstract LLM Extractor Interface.

This interface allows for easy integration of different LLM/VLM providers
(e.g., Unsloth-LLaMA, ERNIE-VLM, commercial APIs).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel


class ExtractionResult(BaseModel):
    """Standard LLM extraction result structure."""
    
    structured_data: Dict[str, Any]
    confidence_scores: Dict[str, float]
    model_version: str
    processing_time_ms: Optional[float] = None
    status: str = "completed"  # completed, partial, failed


class AbstractLLMExtractor(ABC):
    """
    Abstract base class for LLM/VLM extractors.
    
    Implementations should provide:
    - Unsloth-optimized LLaMA integration
    - ERNIE-VLM integration
    - Commercial LLM API integration
    """
    
    @abstractmethod
    async def enrich_financial_data(
        self,
        ocr_result: Dict[str, Any],
        file_content: Optional[bytes] = None
    ) -> ExtractionResult:
        """
        Enrich OCR results with semantic understanding.
        
        Args:
            ocr_result: OCR output dictionary
            file_content: Optional raw file content for vision models
        
        Returns:
            ExtractionResult with structured data
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this LLM extractor."""
        pass
    
    @abstractmethod
    def get_model_version(self) -> str:
        """Get the model version being used."""
        pass
    
    def is_available(self) -> bool:
        """
        Check if the LLM extractor is available.
        
        Returns:
            True if available, False otherwise
        """
        return True

