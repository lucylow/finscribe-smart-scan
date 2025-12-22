"""
Active Learning Export

Judge-winning feature: Export corrected invoices for fine-tuning.
Used when user clicks "Accept & Send to Training".
This directly feeds:
- Unsloth fine-tuning (primary)
- PaddleOCR-VL fine-tuning
- LLaMA-Factory SFT
- Eval datasets
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Training queue files
TRAINING_QUEUE = Path("data/training_queue.jsonl")
UNSLOTH_TRAINING_QUEUE = Path("data/unsloth_training_queue.jsonl")


def _extract_ocr_text(raw_ocr: Union[Dict[str, Any], str]) -> str:
    """
    Extract OCR text from raw OCR output.
    
    Args:
        raw_ocr: Raw OCR output (dict with 'text' field or string)
        
    Returns:
        OCR text as string
    """
    if isinstance(raw_ocr, str):
        return raw_ocr
    elif isinstance(raw_ocr, dict):
        # Try common OCR output formats
        if "text" in raw_ocr:
            return raw_ocr["text"]
        elif "ocr_text" in raw_ocr:
            return raw_ocr["ocr_text"]
        elif "content" in raw_ocr:
            return raw_ocr["content"]
        else:
            # Fallback: convert dict to string representation
            return json.dumps(raw_ocr, ensure_ascii=False)
    else:
        return str(raw_ocr)


def export_training_example(
    raw_ocr: Union[Dict[str, Any], str],
    corrected_invoice: Dict[str, Any],
    invoice_id: Optional[str] = None
) -> Path:
    """
    Export a training example (input/output pair) for fine-tuning.
    
    Exports to both general training queue and Unsloth-specific format.
    
    Args:
        raw_ocr: Raw OCR output (input) - can be dict with 'text' field or string
        corrected_invoice: Human-corrected invoice data (output/gold standard)
        invoice_id: Optional invoice identifier
        
    Returns:
        Path to the training queue file
    """
    # Ensure data directory exists
    TRAINING_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    UNSLOTH_TRAINING_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    
    # Extract OCR text
    ocr_text = _extract_ocr_text(raw_ocr)
    
    # Prepare general training record
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "invoice_id": invoice_id,
        "input": raw_ocr if isinstance(raw_ocr, dict) else {"text": ocr_text},
        "output": corrected_invoice,
    }
    
    # Append to general training queue
    with open(TRAINING_QUEUE, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")
    
    # Prepare Unsloth-specific format (input/output as strings)
    # Format: {"input": "OCR_TEXT:\n...", "output": "{\"vendor\": {...}, ...}"}
    unsloth_record = {
        "input": f"OCR_TEXT:\n{ocr_text}\n\nExtract structured JSON with vendor, invoice_number, dates, "
                 f"line_items (desc, qty, unit_price, line_total), and financial_summary. "
                 f"Output only valid JSON without any explanation.",
        "output": json.dumps(corrected_invoice, ensure_ascii=False),
    }
    
    # Append to Unsloth training queue
    with open(UNSLOTH_TRAINING_QUEUE, "a") as f:
        f.write(json.dumps(unsloth_record, ensure_ascii=False) + "\n")
    
    logger.info(f"Exported training example for invoice {invoice_id} (both formats)")
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


def export_unsloth_training_example(raw_text: str, corrected_json: Dict[str, Any]) -> Path:
    """
    Export training example in Unsloth format (for direct use in fine-tuning).
    
    This is a convenience function that directly exports to Unsloth format.
    Use export_training_example() for general use (exports to both formats).
    
    Args:
        raw_text: OCR-extracted text as string
        corrected_json: Corrected invoice JSON structure
        
    Returns:
        Path to Unsloth training queue file
    """
    UNSLOTH_TRAINING_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    
    record = {
        "input": f"OCR_TEXT:\n{raw_text}\n\nExtract structured JSON with vendor, invoice_number, dates, "
                 f"line_items (desc, qty, unit_price, line_total), and financial_summary. "
                 f"Output only valid JSON without any explanation.",
        "output": json.dumps(corrected_json, ensure_ascii=False),
    }
    
    with open(UNSLOTH_TRAINING_QUEUE, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    logger.info("Exported Unsloth training example")
    return UNSLOTH_TRAINING_QUEUE


def get_training_queue_stats() -> Dict[str, Any]:
    """
    Get statistics about the training queue.
    
    Returns:
        Dictionary with queue statistics
    """
    stats = {
        "total_examples": 0,
        "file_size_bytes": 0,
        "unsloth_examples": 0,
        "unsloth_file_size_bytes": 0,
    }
    
    if TRAINING_QUEUE.exists():
        examples = load_training_queue()
        file_size = TRAINING_QUEUE.stat().st_size
        stats["total_examples"] = len(examples)
        stats["file_size_bytes"] = file_size
        if examples:
            stats["oldest_example"] = examples[0].get("timestamp")
            stats["newest_example"] = examples[-1].get("timestamp")
    
    if UNSLOTH_TRAINING_QUEUE.exists():
        unsloth_examples = []
        with open(UNSLOTH_TRAINING_QUEUE, "r") as f:
            for line in f:
                if line.strip():
                    unsloth_examples.append(json.loads(line))
        stats["unsloth_examples"] = len(unsloth_examples)
        stats["unsloth_file_size_bytes"] = UNSLOTH_TRAINING_QUEUE.stat().st_size
    
    return stats

