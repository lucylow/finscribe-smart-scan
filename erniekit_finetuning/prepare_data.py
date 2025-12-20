#!/usr/bin/env python3
"""
Prepare instruction-response pairs for ERNIE fine-tuning.

Converts active learning data and synthetic invoices into instruction-response pairs
suitable for Supervised Fine-Tuning (SFT) with ERNIE models.
"""

import json
import argparse
import base64
from pathlib import Path
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_active_learning_data(file_path: Path) -> List[Dict[str, Any]]:
    """Load active learning data from JSONL file."""
    entries = []
    if not file_path.exists():
        logger.warning(f"Active learning file not found: {file_path}")
        return entries
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping invalid JSON line: {e}")
    
    logger.info(f"Loaded {len(entries)} entries from active learning data")
    return entries


def create_instruction_pair(
    image_path: str,
    ocr_result: Dict[str, Any],
    ground_truth: Dict[str, Any],
    instruction_type: str = "full_analysis"
) -> Dict[str, Any]:
    """
    Create an instruction-response pair for ERNIE fine-tuning.
    
    Args:
        image_path: Path to invoice image
        ocr_result: OCR output from PaddleOCR-VL
        ground_truth: Expected structured output
        instruction_type: Type of instruction ("full_analysis", "validation", "extraction")
    
    Returns:
        Instruction-response pair in ERNIEKit format
    """
    
    # Build instruction based on type
    if instruction_type == "full_analysis":
        instruction = """<image>
Analyze this financial invoice. Perform these tasks:

1. EXTRACT all key information:
   - Vendor block (name, address, contact)
   - Client/Invoice info (date, number, due date)
   - Line item table (description, quantity, price, total)
   - Tax & discount section
   - Grand total & payment terms

2. VALIDATE arithmetic consistency:
   - Sum of line items = subtotal
   - Subtotal + tax - discounts = grand total

3. RETURN structured JSON with confidence scores.

Preliminary OCR Data:
{ocr_data}""".format(ocr_data=json.dumps(ocr_result, indent=2))
    
    elif instruction_type == "validation":
        instruction = """<image>
Validate the extracted financial data from this invoice. Check:
- Arithmetic consistency (subtotal + tax - discounts = total)
- Date formats are correct
- All required fields are present
- Line item totals are correct

OCR Data:
{ocr_data}

Return validation results with corrections if needed.""".format(ocr_data=json.dumps(ocr_result, indent=2))
    
    else:  # extraction
        instruction = """<image>
Extract structured financial data from this invoice. Return JSON with:
- vendor_block
- client_info
- line_items
- financial_summary
- payment_terms

OCR Data:
{ocr_data}""".format(ocr_data=json.dumps(ocr_result, indent=2))
    
    # Build response (ground truth structured data)
    response = {
        "structured_data": ground_truth.get("structured_data", {}),
        "validation_summary": ground_truth.get("validation_summary", {
            "is_valid": True,
            "math_verified": True,
            "issues": []
        }),
        "confidence_scores": ground_truth.get("confidence_scores", {
            "overall": 0.95
        })
    }
    
    # Format as ERNIEKit conversation format
    pair = {
        "image": image_path,
        "conversations": [
            {
                "role": "human",
                "content": instruction
            },
            {
                "role": "assistant",
                "content": json.dumps(response, indent=2, ensure_ascii=False)
            }
        ]
    }
    
    return pair


def prepare_from_active_learning(
    active_learning_file: Path,
    output_file: Path,
    image_base_dir: Path = None
) -> int:
    """
    Convert active learning data to instruction pairs.
    
    Args:
        active_learning_file: Path to active_learning.jsonl
        output_file: Output JSONL file path
        image_base_dir: Base directory for image paths (optional)
    
    Returns:
        Number of pairs created
    """
    entries = load_active_learning_data(active_learning_file)
    
    if not entries:
        logger.warning("No active learning data found. Consider using synthetic data instead.")
        return 0
    
    pairs = []
    for entry in entries:
        # Extract data from active learning entry
        source_file = entry.get("source_file", "")
        model_output = entry.get("model_output", {})
        validation = entry.get("validation", {})
        
        # Build ground truth from model output (assuming it's correct)
        ground_truth = {
            "structured_data": model_output,
            "validation_summary": validation,
            "confidence_scores": {
                "overall": 0.95
            }
        }
        
        # Create OCR result placeholder (in real scenario, you'd have this)
        ocr_result = {
            "status": "success",
            "tokens": [],
            "bboxes": [],
            "regions": []
        }
        
        # Resolve image path
        if image_base_dir:
            image_path = str(image_base_dir / source_file)
        else:
            image_path = source_file
        
        # Create instruction pair
        pair = create_instruction_pair(
            image_path=image_path,
            ocr_result=ocr_result,
            ground_truth=ground_truth,
            instruction_type="full_analysis"
        )
        pairs.append(pair)
    
    # Write to output file
    with open(output_file, 'w') as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')
    
    logger.info(f"Created {len(pairs)} instruction pairs in {output_file}")
    return len(pairs)


def prepare_from_synthetic_data(
    manifest_file: Path,
    output_file: Path,
    image_dir: Path,
    ground_truth_dir: Path
) -> int:
    """
    Convert synthetic invoice data to instruction pairs.
    
    Args:
        manifest_file: Path to training manifest JSON
        output_file: Output JSONL file path
        image_dir: Directory containing invoice images
        ground_truth_dir: Directory containing ground truth JSON files
    
    Returns:
        Number of pairs created
    """
    if not manifest_file.exists():
        logger.error(f"Manifest file not found: {manifest_file}")
        return 0
    
    with open(manifest_file, 'r') as f:
        manifest = json.load(f)
    
    pairs = []
    for item in manifest:
        image_path = image_dir / item.get("image", "")
        gt_path = ground_truth_dir / item.get("ground_truth", "")
        
        if not image_path.exists():
            logger.warning(f"Image not found: {image_path}")
            continue
        
        if not gt_path.exists():
            logger.warning(f"Ground truth not found: {gt_path}")
            continue
        
        # Load ground truth
        with open(gt_path, 'r') as f:
            ground_truth = json.load(f)
        
        # Create mock OCR result (in real scenario, run PaddleOCR-VL)
        ocr_result = {
            "status": "success",
            "tokens": [],
            "bboxes": [],
            "regions": []
        }
        
        # Create instruction pair
        pair = create_instruction_pair(
            image_path=str(image_path),
            ocr_result=ocr_result,
            ground_truth=ground_truth,
            instruction_type="full_analysis"
        )
        pairs.append(pair)
    
    # Write to output file
    with open(output_file, 'w') as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + '\n')
    
    logger.info(f"Created {len(pairs)} instruction pairs from synthetic data")
    return len(pairs)


def main():
    parser = argparse.ArgumentParser(
        description="Prepare instruction-response pairs for ERNIE fine-tuning"
    )
    parser.add_argument(
        "--active-learning-file",
        type=Path,
        help="Path to active_learning.jsonl file"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Path to training manifest JSON (for synthetic data)"
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        help="Directory containing invoice images"
    )
    parser.add_argument(
        "--ground-truth-dir",
        type=Path,
        help="Directory containing ground truth JSON files"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output JSONL file path"
    )
    
    args = parser.parse_args()
    
    # Determine data source
    if args.active_learning_file:
        count = prepare_from_active_learning(
            active_learning_file=args.active_learning_file,
            output_file=args.output,
            image_base_dir=args.images_dir
        )
    elif args.manifest:
        if not args.images_dir or not args.ground_truth_dir:
            parser.error("--images-dir and --ground-truth-dir required when using --manifest")
        
        count = prepare_from_synthetic_data(
            manifest_file=args.manifest,
            output_file=args.output,
            image_dir=args.images_dir,
            ground_truth_dir=args.ground_truth_dir
        )
    else:
        parser.error("Either --active-learning-file or --manifest must be provided")
    
    logger.info(f"✅ Created {count} instruction pairs in {args.output}")
    logger.info("Next step: Run training with erniekit_finetuning/train_ernie_lora.py")


if __name__ == "__main__":
    main()

