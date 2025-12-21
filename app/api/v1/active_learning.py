"""
Active Learning Endpoint

Accepts corrected invoice data and saves to training queue for future fine-tuning.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class ActiveLearningRequest(BaseModel):
    """Request model for active learning submission."""
    invoice: Dict[str, Any]
    corrections: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


@router.post("/active_learning")
async def submit_active_learning(request: ActiveLearningRequest):
    """
    Submit corrected invoice data to active learning queue.
    
    This endpoint saves corrections to a JSONL file that can be used for
    future fine-tuning of the Unsloth model.
    
    Args:
        request: ActiveLearningRequest with invoice data and corrections
        
    Returns:
        Success message with file path
    """
    try:
        # Get active learning file path
        al_file = os.getenv("ACTIVE_LEARNING_FILE", "data/active_learning.jsonl")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(al_file), exist_ok=True)
        
        # Create entry
        entry = {
            "prompt": request.metadata.get("ocr_text", ""),
            "completion": json.dumps(request.invoice),
            "corrections": request.corrections,
            "meta": {
                **request.metadata,
                "saved_at": datetime.utcnow().isoformat(),
                "source": "frontend_correction"
            }
        }
        
        # Append to file
        with open(al_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        
        logger.info(f"Saved correction to active learning queue: {al_file}")
        
        return {
            "status": "success",
            "message": "Correction saved to training queue",
            "file": al_file,
            "entry_count": _count_entries(al_file)
        }
        
    except Exception as e:
        logger.error(f"Error saving to active learning queue: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save correction: {str(e)}"
        )


def _count_entries(file_path: str) -> int:
    """Count entries in active learning file."""
    try:
        if not os.path.exists(file_path):
            return 0
        with open(file_path, "r") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0

