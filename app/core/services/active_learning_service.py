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
        user_id: Optional[str] = None
    ) -> bool:
        """
        Log user correction to active learning queue.
        
        Args:
            document_id: Unique document identifier
            original_data: Original extracted data
            corrected_data: User-corrected data
            user_id: Optional user identifier
        
        Returns:
            True if logging succeeded, False otherwise
        """
        if not self.enabled:
            return False
        
        log_entry = {
            "document_id": document_id,
            "timestamp": datetime.utcnow().isoformat(),
            "original": original_data,
            "correction": corrected_data,
            "user_id": user_id,
            "type": "correction"
        }
        
        try:
            async with aiofiles.open(self.file_path, mode="a") as f:
                await f.write(json.dumps(log_entry) + "\n")
            logger.info(f"Logged correction for document {document_id}")
            return True
        except Exception as e:
            logger.warning(f"Could not log correction to active learning file: {e}")
            return False
    
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

