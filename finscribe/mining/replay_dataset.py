"""
Hard-sample replay dataset builder
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image

from finscribe.data.formatters import build_instruction_sample


def build_hard_sample_dataset(
    error_dir: Path,
    region_type: str = "totals_section",
) -> List[Dict[str, Any]]:
    """
    Builds a training dataset from logged error cases.
    
    Args:
        error_dir: Directory containing error JSON files
        region_type: Type of region these errors correspond to
        
    Returns:
        List of instruction samples for hard-sample replay
    """
    samples = []
    error_files = list(error_dir.glob("*.json"))
    
    for error_file in error_files:
        try:
            record = json.loads(error_file.read_text())
            
            image_path = record.get("image")
            if not image_path:
                continue
            
            image_path = Path(image_path)
            if not image_path.exists():
                # Try relative to error_dir
                image_path = error_dir.parent / image_path.name
                if not image_path.exists():
                    continue
            
            image = Image.open(image_path).convert("RGB")
            gt = record.get("ground_truth", {})
            
            # Build instruction sample using ground truth
            sample = build_instruction_sample(
                image=image,
                region_type=region_type,
                target=gt,
            )
            
            samples.append(sample)
            
        except Exception as e:
            print(f"Error processing {error_file}: {e}")
            continue
    
    return samples

