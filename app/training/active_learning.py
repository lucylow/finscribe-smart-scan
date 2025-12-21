"""
Active Learning Export

Judge-winning feature: Export corrected invoices for fine-tuning.
Used when user clicks "Accept & Send to Training".
This directly feeds:
- PaddleOCR-VL fine-tuning
- LLaMA-Factory SFT
- Eval datasets
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Training queue file
TRAINING_QUEUE = Path("data/training_queue.jsonl")


def export_training_example(
    raw_ocr: Dict[str, Any],
    corrected_invoice: Dict[str, Any],
    invoice_id: Optional[str] = None
) -> Path:
    """
    Export a training example (input/output pair) for fine-tuning.
    
    Args:
        raw_ocr: Raw OCR output (input)
        corrected_invoice: Human-corrected invoice data (output/gold standard)
        invoice_id: Optional invoice identifier
        
    Returns:
        Path to the training queue file
    """
    # Ensure data directory exists
    TRAINING_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    
    # Prepare training record
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "invoice_id": invoice_id,
        "input": raw_ocr,
        "output": corrected_invoice,
    }
    
    # Append to JSONL file (one record per line)
    with open(TRAINING_QUEUE, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")
    
    logger.info(f"Exported training example for invoice {invoice_id}")
    return TRAINING_QUEUE


def load_training_queue(limit: Optional[int] = None) -> list[Dict[str, Any]]:
    """
    Load training examples from the queue.
    
    Args:
        limit: Optional limit on number of examples to load
        
    Returns:
        List of training examples
    """
    if not TRAINING_QUEUE.exists():
        return []
    
    examples = []
    with open(TRAINING_QUEUE, "r") as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))
                if limit and len(examples) >= limit:
                    break
    
    return examples


def clear_training_queue():
    """Clear the training queue (use with caution)."""
    if TRAINING_QUEUE.exists():
        TRAINING_QUEUE.unlink()
        logger.info("Cleared training queue")


def get_training_queue_stats() -> Dict[str, Any]:
    """
    Get statistics about the training queue.
    
    Returns:
        Dictionary with queue statistics
    """
    if not TRAINING_QUEUE.exists():
        return {
            "total_examples": 0,
            "file_size_bytes": 0,
        }
    
    examples = load_training_queue()
    file_size = TRAINING_QUEUE.stat().st_size
    
    return {
        "total_examples": len(examples),
        "file_size_bytes": file_size,
        "oldest_example": examples[0]["timestamp"] if examples else None,
        "newest_example": examples[-1]["timestamp"] if examples else None,
    }

