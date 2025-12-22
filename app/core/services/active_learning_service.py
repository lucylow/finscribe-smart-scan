"""
Active Learning Service - Manages active learning data collection.

This service handles:
- Logging corrections to active learning queue
- Exporting data for training
- Managing active learning file
"""

import json
import aiofiles
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ...config.settings import load_config

logger = logging.getLogger(__name__)


class ActiveLearningService:
    """
    Service for managing active learning data.
    
    Responsibilities:
    - Logging corrections to active learning queue
    - Exporting data for training
    - Managing active learning file
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize active learning service with configuration."""
        self.config = config or load_config()
        
        al_config = self.config.get("active_learning", {})
        self.enabled = al_config.get("enabled", True)
        self.file_path = al_config.get("file_path", "./data/active_learning.jsonl")
        
        # Ensure directory exists
        import os
        os.makedirs(os.path.dirname(self.file_path) if os.path.dirname(self.file_path) else ".", exist_ok=True)
    
    async def log_extraction(
        self,
        document_id: str,
        filename: str,
        enriched_data: Dict[str, Any],
        validation: Dict[str, Any],
        model_type: str = "fine_tuned"
    ) -> bool:
        """
        Log extraction data to active learning queue.
        
        Args:
            document_id: Unique document identifier
            filename: Original filename
            enriched_data: Extracted structured data
            validation: Validation results
            model_type: Model type used
        
        Returns:
            True if logging succeeded, False otherwise
        """
        if not self.enabled or model_type != "fine_tuned":
            return False
        
        log_entry = {
            "document_id": document_id,
            "source_file": filename,
            "timestamp": datetime.utcnow().isoformat(),
            "model_output": enriched_data.get("structured_data", {}),
            "validation": validation,
            "needs_review": validation.get("needs_review", False),
            "difficulty_label": "medium" if validation.get("needs_review") else "easy",
            "error_type": validation.get("issues", [])[:1] if validation.get("issues") else None
        }
        
        try:
            async with aiofiles.open(self.file_path, mode="a") as f:
                await f.write(json.dumps(log_entry) + "\n")
            logger.info(f"Logged active learning data for document {document_id}")
            return True
        except Exception as e:
            logger.warning(f"Could not log to active learning file: {e}")
            return False
    
    async def log_correction(
        self,
        document_id: str,
        original_data: Dict[str, Any],
        corrected_data: Dict[str, Any],
        user_id: Optional[str] = None,
        ocr_output: Optional[Dict[str, Any]] = None,
        structured_ocr_output: Optional[str] = None,
        image_path: Optional[str] = None
    ) -> bool:
        """
        Log user correction to active learning queue with structured OCR output.
        
        This method generates a training sample that includes:
        1. The original pre-processed image (path reference)
        2. The original structured OCR output
        3. The final, human-corrected JSON output
        
        This ensures the fine-tuning data directly addresses the model's failure points.
        
        Args:
            document_id: Unique document identifier
            original_data: Original extracted data (model output)
            corrected_data: User-corrected data (ground truth)
            user_id: Optional user identifier
            ocr_output: Original raw OCR output (for reference)
            structured_ocr_output: Structured OCR output with semantic labels (for training)
            image_path: Path to pre-processed image (for training)
        
        Returns:
            True if logging succeeded, False otherwise
        """
        if not self.enabled:
            return False
        
        # Generate training sample format
        training_sample = self._generate_training_sample(
            document_id=document_id,
            original_data=original_data,
            corrected_data=corrected_data,
            ocr_output=ocr_output,
            structured_ocr_output=structured_ocr_output,
            image_path=image_path,
            user_id=user_id
        )
        
        try:
            async with aiofiles.open(self.file_path, mode="a") as f:
                await f.write(json.dumps(training_sample) + "\n")
            logger.info(f"Logged correction with training sample for document {document_id}")
            return True
        except Exception as e:
            logger.warning(f"Could not log correction to active learning file: {e}")
            return False
    
    def _generate_training_sample(
        self,
        document_id: str,
        original_data: Dict[str, Any],
        corrected_data: Dict[str, Any],
        ocr_output: Optional[Dict[str, Any]] = None,
        structured_ocr_output: Optional[str] = None,
        image_path: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a training sample from human correction.
        
        The training sample format is optimized for fine-tuning:
        - prompt: Structured OCR output (input to LLM)
        - completion: Human-corrected JSON (target output)
        - metadata: Additional context for training
        
        Args:
            document_id: Document identifier
            original_data: Original model output
            corrected_data: Human-corrected output
            ocr_output: Raw OCR output
            structured_ocr_output: Structured OCR with semantic labels
            image_path: Path to pre-processed image
            user_id: User identifier
            
        Returns:
            Training sample dictionary
        """
        # If structured OCR output not provided, try to generate it from raw OCR
        if not structured_ocr_output and ocr_output:
            try:
                import sys
                import os
                # Try to import semantic filtering
                ocr_module_path = os.path.join(
                    os.path.dirname(__file__), '..', '..', 'ocr'
                )
                if os.path.exists(ocr_module_path):
                    sys.path.insert(0, ocr_module_path)
                    try:
                        from paddle_wrapper import get_structured_ocr_output
                        structured_ocr_output = get_structured_ocr_output(ocr_output)
                        logger.debug("Generated structured OCR output from raw OCR")
                    except ImportError:
                        pass
            except Exception as e:
                logger.warning(f"Could not generate structured OCR output: {e}")
        
        # Fallback: use raw text if structured output not available
        if not structured_ocr_output:
            if ocr_output and isinstance(ocr_output, dict):
                structured_ocr_output = ocr_output.get("text", "")
            else:
                structured_ocr_output = ""
        
        # Build training sample
        training_sample = {
            "document_id": document_id,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "correction",
            
            # Training data format (for fine-tuning)
            "prompt": structured_ocr_output,  # Input: structured OCR output
            "completion": json.dumps(corrected_data, indent=2),  # Target: corrected JSON
            
            # Metadata for training pipeline
            "metadata": {
                "user_id": user_id,
                "image_path": image_path,
                "model_version": "unsloth-finscribe",
                "correction_type": self._identify_correction_type(original_data, corrected_data),
                "difficulty": self._assess_difficulty(original_data, corrected_data)
            },
            
            # Original data for reference
            "original_output": original_data,
            "corrected_output": corrected_data,
            
            # OCR context
            "ocr_context": {
                "raw_ocr": ocr_output if ocr_output else None,
                "structured_ocr": structured_ocr_output
            }
        }
        
        return training_sample
    
    def _identify_correction_type(
        self,
        original: Dict[str, Any],
        corrected: Dict[str, Any]
    ) -> str:
        """
        Identify the type of correction made.
        
        Returns:
            Correction type: "arithmetic", "field_missing", "field_incorrect", "format", "other"
        """
        # Check for arithmetic corrections
        orig_fs = original.get("financial_summary", {})
        corr_fs = corrected.get("financial_summary", {})
        
        if orig_fs.get("grand_total") != corr_fs.get("grand_total"):
            return "arithmetic"
        
        # Check for missing fields
        orig_keys = set(original.keys())
        corr_keys = set(corrected.keys())
        if corr_keys - orig_keys:
            return "field_missing"
        
        # Check for incorrect field values
        for key in orig_keys & corr_keys:
            if original.get(key) != corrected.get(key):
                return "field_incorrect"
        
        return "other"
    
    def _assess_difficulty(
        self,
        original: Dict[str, Any],
        corrected: Dict[str, Any]
    ) -> str:
        """
        Assess the difficulty of the correction.
        
        Returns:
            Difficulty level: "easy", "medium", "hard"
        """
        correction_type = self._identify_correction_type(original, corrected)
        
        if correction_type == "arithmetic":
            return "hard"
        elif correction_type == "field_missing":
            return "medium"
        elif correction_type == "field_incorrect":
            return "easy"
        else:
            return "medium"
    
    async def export_for_training(self, limit: Optional[int] = None) -> list:
        """
        Export active learning data for training.
        
        Args:
            limit: Optional limit on number of records to export
        
        Returns:
            List of training records
        """
        records = []
        
        try:
            async with aiofiles.open(self.file_path, mode="r") as f:
                async for line in f:
                    if line.strip():
                        records.append(json.loads(line))
                        if limit and len(records) >= limit:
                            break
        except FileNotFoundError:
            logger.warning(f"Active learning file not found: {self.file_path}")
        except Exception as e:
            logger.error(f"Error exporting active learning data: {e}")
        
        return records

