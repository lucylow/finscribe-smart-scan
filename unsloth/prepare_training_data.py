"""
Training Data Preparation Utility for Unsloth

Converts various data formats into Unsloth training format (input/output JSONL).
Supports:
- Active learning queue
- Existing training datasets
- Synthetic invoice data
- Manual corrections
"""
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """Load JSONL file."""
    data = []
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return data
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse line in {file_path}: {e}")
    
    return data


def extract_ocr_text(record: Dict[str, Any]) -> str:
    """Extract OCR text from various record formats."""
    # Try different field names
    if "input" in record:
        input_data = record["input"]
        if isinstance(input_data, str):
            return input_data
        elif isinstance(input_data, dict):
            return input_data.get("text", input_data.get("ocr_text", json.dumps(input_data)))
    
    if "prompt" in record:
        prompt = record["prompt"]
        if isinstance(prompt, str):
            return prompt.replace("OCR_TEXT:\n", "").strip()
        return str(prompt)
    
    if "ocr_text" in record:
        return record["ocr_text"]
    
    if "text" in record:
        return record["text"]
    
    # Fallback
    return json.dumps(record.get("raw_ocr", record.get("ocr", "")))


def extract_output_json(record: Dict[str, Any]) -> str:
    """Extract output JSON from various record formats."""
    if "output" in record:
        output = record["output"]
        if isinstance(output, str):
            # Try to parse as JSON to validate
            try:
                json.loads(output)
                return output
            except:
                return json.dumps(output)
        else:
            return json.dumps(output, ensure_ascii=False)
    
    if "completion" in record:
        completion = record["completion"]
        if isinstance(completion, str):
            try:
                json.loads(completion)
                return completion
            except:
                return json.dumps(completion)
        return json.dumps(completion, ensure_ascii=False)
    
    if "corrected_invoice" in record:
        return json.dumps(record["corrected_invoice"], ensure_ascii=False)
    
    # Fallback: use the whole record as output
    return json.dumps(record, ensure_ascii=False)


def convert_to_unsloth_format(records: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Convert records to Unsloth training format."""
    unsloth_records = []
    
    for record in records:
        try:
            ocr_text = extract_ocr_text(record)
            output_json = extract_output_json(record)
            
            # Format as Unsloth expects
            unsloth_record = {
                "input": f"OCR_TEXT:\n{ocr_text}\n\nExtract structured JSON with vendor, invoice_number, dates, "
                         f"line_items (desc, qty, unit_price, line_total), and financial_summary. "
                         f"Output only valid JSON without any explanation.",
                "output": output_json,
            }
            
            unsloth_records.append(unsloth_record)
        except Exception as e:
            logger.warning(f"Failed to convert record: {e}")
            continue
    
    return unsloth_records


def merge_datasets(input_files: List[Path], output_file: Path, shuffle: bool = True):
    """Merge multiple datasets into one Unsloth training file."""
    all_records = []
    
    for input_file in input_files:
        logger.info(f"Loading {input_file}...")
        records = load_jsonl(input_file)
        logger.info(f"Loaded {len(records)} records from {input_file}")
        all_records.extend(records)
    
    logger.info(f"Total records: {len(all_records)}")
    
    # Convert to Unsloth format
    unsloth_records = convert_to_unsloth_format(all_records)
    logger.info(f"Converted {len(unsloth_records)} records to Unsloth format")
    
    # Shuffle if requested
    if shuffle:
        import random
        random.seed(42)
        random.shuffle(unsloth_records)
        logger.info("Shuffled dataset")
    
    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for record in unsloth_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    logger.info(f"Wrote {len(unsloth_records)} records to {output_file}")
    
    # Split into train/val if requested
    return unsloth_records


def split_train_val(records: List[Dict[str, str]], train_file: Path, val_file: Path, val_ratio: float = 0.1):
    """Split records into training and validation sets."""
    import random
    random.seed(42)
    random.shuffle(records)
    
    split_idx = int(len(records) * (1 - val_ratio))
    train_records = records[:split_idx]
    val_records = records[split_idx:]
    
    logger.info(f"Splitting: {len(train_records)} train, {len(val_records)} val")
    
    # Write train
    train_file.parent.mkdir(parents=True, exist_ok=True)
    with open(train_file, "w", encoding="utf-8") as f:
        for record in train_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    # Write val
    val_file.parent.mkdir(parents=True, exist_ok=True)
    with open(val_file, "w", encoding="utf-8") as f:
        for record in val_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    logger.info(f"Wrote train to {train_file}")
    logger.info(f"Wrote val to {val_file}")


def main():
    parser = argparse.ArgumentParser(description="Prepare training data for Unsloth fine-tuning")
    parser.add_argument("--input", type=str, nargs="+", required=True,
                       help="Input JSONL files (can specify multiple)")
    parser.add_argument("--output", type=str, default="./data/unsloth_train.jsonl",
                       help="Output training file")
    parser.add_argument("--val_output", type=str, default="./data/unsloth_val.jsonl",
                       help="Output validation file (if splitting)")
    parser.add_argument("--val_ratio", type=float, default=0.1,
                       help="Validation split ratio (0.0 to 1.0)")
    parser.add_argument("--no_shuffle", action="store_true",
                       help="Don't shuffle the dataset")
    parser.add_argument("--split", action="store_true",
                       help="Split into train/val sets")
    
    args = parser.parse_args()
    
    # Convert input paths
    input_files = [Path(f) for f in args.input]
    output_file = Path(args.output)
    val_file = Path(args.val_output) if args.split else None
    
    # Merge and convert
    records = merge_datasets(input_files, output_file, shuffle=not args.no_shuffle)
    
    # Split if requested
    if args.split and val_file:
        split_train_val(records, output_file, val_file, args.val_ratio)
    
    logger.info("Data preparation complete!")


if __name__ == "__main__":
    main()

