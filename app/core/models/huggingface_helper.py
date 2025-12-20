"""
HuggingFace integration helper for ERNIE models.
Supports loading models from HuggingFace Hub and ERNIE collections.
"""
import logging
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class HuggingFaceHelper:
    """Helper class for HuggingFace model integration."""
    
    # ERNIE model collections on HuggingFace
    ERNIE_COLLECTIONS = {
        "ernie-5": {
            "collection_url": "https://huggingface.co/collections/baidu/ernie-5",
            "models": [
                "baidu/ERNIE-5",
                "baidu/ERNIE-5-8B",
                "baidu/ERNIE-5-28B"
            ]
        },
        "ernie-4.5": {
            "collection_url": "https://huggingface.co/collections/baidu/ernie-45",
            "models": [
                "baidu/ERNIE-4.5-VL-28B-A3B-Thinking",
                "baidu/ERNIE-4.5-8B",
                "baidu/ERNIE-4.5-0.3B"
            ]
        }
    }
    
    # PaddleOCR models
    PADDLEOCR_MODELS = {
        "paddleocr-vl": {
            "model_name": "PaddlePaddle/PaddleOCR-VL",
            "collection_url": "https://huggingface.co/PaddlePaddle/PaddleOCR-VL"
        }
    }
    
    @staticmethod
    def get_model_info(model_name: str) -> Dict[str, Any]:
        """
        Get information about an ERNIE model from HuggingFace.
        
        Args:
            model_name: Name of the model (e.g., "baidu/ERNIE-5")
            
        Returns:
            Dictionary with model information
        """
        # Check ERNIE 5 models
        if any(model in model_name for model in HuggingFaceHelper.ERNIE_COLLECTIONS["ernie-5"]["models"]):
            return {
                "family": "ernie-5",
                "collection_url": HuggingFaceHelper.ERNIE_COLLECTIONS["ernie-5"]["collection_url"],
                "huggingface_url": f"https://huggingface.co/{model_name}",
                "supports_vl": "VL" in model_name or "vl" in model_name,
                "supports_thinking": True
            }
        
        # Check ERNIE 4.5 models
        if any(model in model_name for model in HuggingFaceHelper.ERNIE_COLLECTIONS["ernie-4.5"]["models"]):
            return {
                "family": "ernie-4.5",
                "collection_url": HuggingFaceHelper.ERNIE_COLLECTIONS["ernie-4.5"]["collection_url"],
                "huggingface_url": f"https://huggingface.co/{model_name}",
                "supports_vl": "VL" in model_name or "vl" in model_name,
                "supports_thinking": "Thinking" in model_name or "thinking" in model_name
            }
        
        # Default info
        return {
            "family": "unknown",
            "huggingface_url": f"https://huggingface.co/{model_name}",
            "supports_vl": False,
            "supports_thinking": False
        }
    
    @staticmethod
    def validate_huggingface_token(token: Optional[str] = None) -> bool:
        """
        Validate if a HuggingFace token is available.
        
        Args:
            token: Optional token to validate. If None, checks environment.
            
        Returns:
            True if token is available
        """
        if token:
            return len(token.strip()) > 0
        
        # Check environment
        hf_token = os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN")
        return hf_token is not None and len(hf_token.strip()) > 0
    
    @staticmethod
    def get_recommended_model(use_case: str = "financial_document") -> str:
        """
        Get recommended ERNIE model for a specific use case.
        
        Args:
            use_case: Use case identifier (e.g., "financial_document", "ocr", "general")
            
        Returns:
            Recommended model name
        """
        recommendations = {
            "financial_document": "baidu/ERNIE-5",  # Best for financial documents
            "ocr": "baidu/ERNIE-4.5-VL-28B-A3B-Thinking",  # Best for OCR tasks
            "general": "baidu/ERNIE-5",  # General purpose
            "fast": "baidu/ERNIE-4.5-0.3B"  # Fast inference
        }
        
        return recommendations.get(use_case, "baidu/ERNIE-5")
    
    @staticmethod
    def get_model_collection_url(family: str) -> Optional[str]:
        """
        Get the HuggingFace collection URL for an ERNIE model family.
        
        Args:
            family: Model family (e.g., "ernie-5", "ernie-4.5")
            
        Returns:
            Collection URL or None
        """
        collection = HuggingFaceHelper.ERNIE_COLLECTIONS.get(family)
        if collection:
            return collection["collection_url"]
        return None

