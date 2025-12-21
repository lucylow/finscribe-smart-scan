"""
Error logging for hard-sample mining
"""

import json
from pathlib import Path
from typing import Dict, Any


ERROR_DIR = Path("data/hard_samples")


def log_error(
    image_path: str,
    gt: Dict[str, Any],
    pred: Dict[str, Any],
    error_type: str,
) -> Path:
    """
    Logs an error case for hard-sample mining.
    
    Args:
        image_path: Path to the image that caused the error
        gt: Ground truth data
        pred: Predicted data
        error_type: Type of error (e.g., "TOTAL_MISMATCH", "TABLE_STRUCTURE_ERROR")
        
    Returns:
        Path to the saved error record
    """
    ERROR_DIR.mkdir(parents=True, exist_ok=True)
    
    record = {
        "image": image_path,
        "ground_truth": gt,
        "prediction": pred,
        "error_type": error_type,
    }
    
    # Create filename from image path and error type
    image_stem = Path(image_path).stem
    out_file = ERROR_DIR / f"{image_stem}_{error_type}.json"
    
    # Handle duplicate filenames
    counter = 1
    while out_file.exists():
        out_file = ERROR_DIR / f"{image_stem}_{error_type}_{counter}.json"
        counter += 1
    
    out_file.write_text(json.dumps(record, indent=2))
    
    return out_file


