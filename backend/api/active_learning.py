"""Active learning endpoint"""
import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/active_learning", tags=["training"])

QUEUE_FILE = Path("data") / "active_learning_queue.jsonl"


@router.post("")
async def accept_correction(correction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accept corrected invoice and append to training queue.
    
    Request body should contain:
    - invoice: corrected structured invoice
    - corrections: metadata about what was corrected
    - metadata: additional metadata (ocr_text, invoice_id, confidence)
    """
    try:
        # Ensure data directory exists
        QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare entry
        entry = {
            "invoice": correction.get("invoice", {}),
            "corrections": correction.get("corrections", {}),
            "metadata": correction.get("metadata", {}),
            "timestamp": str(Path(__file__).stat().st_mtime)  # Simple timestamp
        }
        
        # Append to JSONL file
        with open(QUEUE_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        
        # Count entries
        entry_count = sum(1 for _ in open(QUEUE_FILE)) if QUEUE_FILE.exists() else 0
        
        logger.info(f"Saved correction to training queue (total: {entry_count})")
        
        return {
            "status": "saved",
            "queue_file": str(QUEUE_FILE),
            "entry_count": entry_count
        }
        
    except Exception as e:
        logger.error(f"Error saving correction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save correction: {str(e)}")

