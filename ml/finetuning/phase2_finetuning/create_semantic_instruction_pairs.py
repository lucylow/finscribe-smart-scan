#!/usr/bin/env python3
"""
Enhanced Instruction Pair Generator for Semantic Understanding

This script creates diverse instruction-completion pairs that train PaddleOCR-VL
to understand semantic structure and logic in financial documents, not just extract text.

Prompt Types Generated:
1. Field Extraction - Extract specific key fields
2. Full JSON Parsing - Parse entire document into structured JSON
3. Table Reconstruction - Convert tables to structured formats (CSV/JSON)
4. Logical Reasoning - Verify arithmetic and validate consistency
5. Summarization - Provide concise summaries of complex data
"""

import json
import sys
import random
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Prompt templates for different instruction types
PROMPT_TEMPLATES = {
    "field_extraction": [
        "<image>\nExtract the '{field}' from this document.",
        "<image>\nWhat is the {field} on this invoice?",
        "<image>\nFind and extract the {field} field.",
        "<image>\nIdentify the {field} in this financial document.",
    ],
    "full_json_parsing": [
        "<image>\nParse this entire invoice into a JSON object with keys for vendor, date, line_items, and totals.",
        "<image>\nConvert this invoice to structured JSON format with all fields organized hierarchically.",
        "<image>\nExtract all information from this document and organize it into a complete JSON structure.",
        "<image>\nAnalyze this invoice and extract all fields into structured JSON.",
    ],
    "table_reconstruction": [
        "<image>\nConvert this financial table to CSV format, preserving all headers and row data.",
        "<image>\nExtract the line items table and format it as a structured JSON array.",
        "<image>\nParse the line item table into a JSON array with columns: description, quantity, unit_price, line_total.",
        "<image>\nReconstruct the table structure from this invoice as structured data.",
    ],
    "logical_reasoning": [
        "<image>\nVerify the arithmetic on this invoice. Check if subtotal + tax equals total.",
        "<image>\nValidate the calculations on this invoice. Verify that all line item totals sum correctly.",
        "<image>\nCheck if the invoice totals are mathematically correct. Calculate subtotal + tax - discount and compare with grand total.",
        "<image>\nPerform arithmetic validation on this invoice. Verify each line item calculation and the final totals.",
    ],
    "summarization": [
        "<image>\nSummarize this invoice by listing the vendor name, invoice total, and number of line items.",
        "<image>\nProvide a concise summary of this invoice including key details: vendor, date, total amount, and payment terms.",
        "<image>\nSummarize this financial document by extracting the most important information: who, what, when, and how much.",
        "<image>\nGive me a brief overview of this invoice: vendor, client, total amount, and due date.",
    ],
}


def calculate_line_item_total(item: Dict) -> float:
    """Calculate total for a line item."""
    subtotal = item['quantity'] * item['unit_price']
    tax_amount = subtotal * (item.get('tax_rate', 0.0) / 100)
    discount = item.get('discount', 0.0)
    return round(subtotal + tax_amount - discount, 2)


def verify_invoice_arithmetic(data: Dict) -> Dict:
    """
    Verify arithmetic on invoice and return validation results.
    
    Returns:
        Dict with validation results including correctness flags and calculated values
    """
    # Calculate line item totals
    calculated_line_totals = []
    for item in data['items']:
        calculated_total = calculate_line_item_total(item)
        calculated_line_totals.append(calculated_total)
    
    # Sum all line item totals
    calculated_subtotal = sum(item['quantity'] * item['unit_price'] for item in data['items'])
    
    # Calculate tax
    calculated_tax = sum(
        (item['quantity'] * item['unit_price']) * (item.get('tax_rate', 0.0) / 100)
        for item in data['items']
    )
    
    # Get discount total
    discount_total = data.get('discount_total', 0.0)
    
    # Calculate grand total
    calculated_grand_total = round(calculated_subtotal + calculated_tax - discount_total, 2)
    
    # Compare with ground truth
    subtotal_correct = abs(calculated_subtotal - data['subtotal']) < 0.01
    tax_correct = abs(calculated_tax - data['tax_total']) < 0.01
    total_correct = abs(calculated_grand_total - data['grand_total']) < 0.01
    
    return {
        "subtotal_correct": subtotal_correct,
        "tax_correct": tax_correct,
        "total_correct": total_correct,
        "calculated_subtotal": round(calculated_subtotal, 2),
        "calculated_tax": round(calculated_tax, 2),
        "calculated_total": calculated_grand_total,
        "ground_truth_subtotal": data['subtotal'],
        "ground_truth_tax": data['tax_total'],
        "ground_truth_total": data['grand_total'],
        "line_items_valid": all(
            abs(calculated_line_totals[i] - calculate_line_item_total(data['items'][i])) < 0.01
            for i in range(len(data['items']))
        )
    }


def create_field_extraction_pairs(data: Dict, image_path: str) -> List[Dict]:
    """Create instruction pairs for field extraction tasks."""
    pairs = []
    
    # Define fields to extract with their paths in the data structure
    fields_to_extract = [
        ("Vendor Name", "vendor.name"),
        ("Invoice Number", "invoice_id"),
        ("Invoice Date", "issue_date"),
        ("Due Date", "due_date"),
        ("Invoice Total", "grand_total"),
        ("Currency", "currency"),
        ("Client Name", "client.name"),
        ("Subtotal", "subtotal"),
        ("Tax Total", "tax_total"),
        ("Payment Terms", "payment_terms"),
    ]
    
    for field_name, field_path in fields_to_extract:
        # Get field value
        keys = field_path.split('.')
        value = data
        try:
            for key in keys:
                value = value[key]
        except (KeyError, TypeError):
            continue
        
        # Select random prompt template
        prompt_template = random.choice(PROMPT_TEMPLATES["field_extraction"])
        prompt = prompt_template.format(field=field_name)
        
        # Create response
        if isinstance(value, (int, float)):
            if field_path == "grand_total" or field_path == "subtotal" or field_path == "tax_total":
                response = json.dumps({
                    "field": field_name,
                    "value": f"{data['currency']} {value:.2f}" if 'currency' in data else f"{value:.2f}",
                    "numeric_value": value
                }, ensure_ascii=False)
            else:
                response = json.dumps({
                    "field": field_name,
                    "value": str(value),
                    "numeric_value": value
                }, ensure_ascii=False)
        else:
            response = json.dumps({
                "field": field_name,
                "value": str(value)
            }, ensure_ascii=False)
        
        pairs.append({
            "image": image_path,
            "conversations": [
                {"role": "human", "content": prompt},
                {"role": "assistant", "content": response}
            ],
            "instruction_type": "field_extraction",
            "field_name": field_name
        })
    
    return pairs


def create_full_json_parsing_pair(data: Dict, image_path: str) -> Dict:
    """Create instruction pair for full JSON parsing."""
    prompt_template = random.choice(PROMPT_TEMPLATES["full_json_parsing"])
    
    # Create comprehensive JSON structure
    full_json = {
        "document_type": "invoice",
        "invoice_number": data['invoice_id'],
        "issue_date": data['issue_date'],
        "due_date": data['due_date'],
        "currency": data['currency'],
        "vendor": {
            "name": data['vendor']['name'],
            "address": f"{data['vendor']['address']}, {data['vendor']['city']}, {data['vendor']['country']} {data['vendor']['postal_code']}",
            "contact": {
                "phone": data['vendor']['phone'],
                "email": data['vendor']['email'],
                "tax_id": data['vendor']['tax_id']
            }
        },
        "client": {
            "name": data['client']['name'],
            "address": f"{data['client']['address']}, {data['client']['city']}, {data['client']['country']} {data['client']['postal_code']}"
        },
        "line_items": [
            {
                "description": item['description'],
                "quantity": item['quantity'],
                "unit_price": item['unit_price'],
                "line_total": calculate_line_item_total(item)
            }
            for item in data['items']
        ],
        "totals": {
            "subtotal": data['subtotal'],
            "tax_total": data['tax_total'],
            "discount_total": data.get('discount_total', 0.0),
            "grand_total": data['grand_total']
        },
        "payment_terms": data['payment_terms'],
        "notes": data.get('notes', '')
    }
    
    response = json.dumps(full_json, ensure_ascii=False, indent=2)
    
    return {
        "image": image_path,
        "conversations": [
            {"role": "human", "content": prompt_template},
            {"role": "assistant", "content": response}
        ],
        "instruction_type": "full_json_parsing"
    }


def create_table_reconstruction_pairs(data: Dict, image_path: str) -> List[Dict]:
    """Create instruction pairs for table reconstruction tasks."""
    pairs = []
    
    # CSV format
    prompt_template_csv = "<image>\nConvert this financial table to CSV format, preserving all headers and row data."
    
    # Build CSV
    csv_lines = ["Description,Quantity,Unit Price,Line Total"]
    for item in data['items']:
        line_total = calculate_line_item_total(item)
        csv_lines.append(
            f'"{item["description"]}",{item["quantity"]},{item["unit_price"]:.2f},{line_total:.2f}'
        )
    csv_response = "\n".join(csv_lines)
    
    pairs.append({
        "image": image_path,
        "conversations": [
            {"role": "human", "content": prompt_template_csv},
            {"role": "assistant", "content": csv_response}
        ],
        "instruction_type": "table_reconstruction",
        "format": "csv"
    })
    
    # JSON array format
    prompt_template_json = random.choice(PROMPT_TEMPLATES["table_reconstruction"])
    
    table_items = [
        {
            "description": item['description'],
            "quantity": item['quantity'],
            "unit_price": item['unit_price'],
            "line_total": calculate_line_item_total(item)
        }
        for item in data['items']
    ]
    
    json_response = json.dumps(table_items, ensure_ascii=False, indent=2)
    
    pairs.append({
        "image": image_path,
        "conversations": [
            {"role": "human", "content": prompt_template_json},
            {"role": "assistant", "content": json_response}
        ],
        "instruction_type": "table_reconstruction",
        "format": "json"
    })
    
    return pairs


def create_logical_reasoning_pair(data: Dict, image_path: str) -> Dict:
    """Create instruction pair for logical reasoning/arithmetic validation."""
    prompt_template = random.choice(PROMPT_TEMPLATES["logical_reasoning"])
    
    validation_result = verify_invoice_arithmetic(data)
    
    response = json.dumps(validation_result, ensure_ascii=False, indent=2)
    
    return {
        "image": image_path,
        "conversations": [
            {"role": "human", "content": prompt_template},
            {"role": "assistant", "content": response}
        ],
        "instruction_type": "logical_reasoning"
    }


def create_summarization_pair(data: Dict, image_path: str) -> Dict:
    """Create instruction pair for document summarization."""
    prompt_template = random.choice(PROMPT_TEMPLATES["summarization"])
    
    summary = {
        "vendor": data['vendor']['name'],
        "client": data['client']['name'],
        "invoice_number": data['invoice_id'],
        "date": data['issue_date'],
        "due_date": data['due_date'],
        "total_amount": f"{data['currency']} {data['grand_total']:.2f}",
        "number_of_items": len(data['items']),
        "payment_terms": data['payment_terms']
    }
    
    # Create a natural language summary
    summary_text = (
        f"Vendor: {summary['vendor']}\n"
        f"Client: {summary['client']}\n"
        f"Invoice Number: {summary['invoice_number']}\n"
        f"Date: {summary['date']}\n"
        f"Due Date: {summary['due_date']}\n"
        f"Total Amount: {summary['total_amount']}\n"
        f"Number of Line Items: {summary['number_of_items']}\n"
        f"Payment Terms: {summary['payment_terms']}"
    )
    
    # Also provide structured format
    response = json.dumps(summary, ensure_ascii=False, indent=2)
    
    return {
        "image": image_path,
        "conversations": [
            {"role": "human", "content": prompt_template},
            {"role": "assistant", "content": response}
        ],
        "instruction_type": "summarization"
    }


def create_semantic_instruction_pairs(metadata_path: str, image_path: str, 
                                      include_types: Optional[List[str]] = None) -> List[Dict]:
    """
    Create diverse instruction-completion pairs for semantic understanding.
    
    Args:
        metadata_path: Path to JSON metadata file
        image_path: Path to invoice image
        include_types: List of instruction types to include. If None, includes all types.
                      Options: "field_extraction", "full_json_parsing", "table_reconstruction",
                               "logical_reasoning", "summarization"
    
    Returns:
        List of instruction-response pair dictionaries
    """
    with open(metadata_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    all_pairs = []
    
    if include_types is None:
        include_types = ["field_extraction", "full_json_parsing", "table_reconstruction",
                        "logical_reasoning", "summarization"]
    
    # Generate pairs for each instruction type
    if "field_extraction" in include_types:
        all_pairs.extend(create_field_extraction_pairs(data, image_path))
    
    if "full_json_parsing" in include_types:
        all_pairs.append(create_full_json_parsing_pair(data, image_path))
    
    if "table_reconstruction" in include_types:
        all_pairs.extend(create_table_reconstruction_pairs(data, image_path))
    
    if "logical_reasoning" in include_types:
        all_pairs.append(create_logical_reasoning_pair(data, image_path))
    
    if "summarization" in include_types:
        all_pairs.append(create_summarization_pair(data, image_path))
    
    return all_pairs


def process_manifest(manifest_path: str, output_path: str, 
                    base_dir: Path = None,
                    include_types: Optional[List[str]] = None,
                    samples_per_invoice: Optional[int] = None) -> int:
    """
    Process training manifest and create semantic instruction pairs.
    
    Args:
        manifest_path: Path to training_manifest.json
        output_path: Path to output JSONL file
        base_dir: Base directory for resolving relative paths
        include_types: Instruction types to include (None = all)
        samples_per_invoice: If set, randomly sample this many pairs per invoice
    
    Returns:
        Number of instruction pairs created
    """
    if base_dir is None:
        base_dir = Path(manifest_path).parent
    
    # Load training manifest
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    all_training_data = []
    
    # Process each invoice
    for entry in tqdm(manifest, desc="Creating semantic instruction pairs"):
        try:
            # Resolve paths
            metadata_file = base_dir / Path(entry['ground_truth_path']).name
            if not metadata_file.exists():
                metadata_file = Path(entry['ground_truth_path'])
                if not metadata_file.is_absolute():
                    metadata_file = base_dir / metadata_file
            
            image_file = Path(entry['image_path'])
            if not image_file.is_absolute():
                image_file = base_dir / image_file
            
            # Verify files exist
            if not metadata_file.exists():
                logger.warning(f"Metadata file not found: {metadata_file}")
                continue
            if not image_file.exists():
                logger.warning(f"Image file not found: {image_file}")
                continue
            
            # Create instruction pairs
            pairs = create_semantic_instruction_pairs(
                str(metadata_file), 
                str(image_file),
                include_types=include_types
            )
            
            # Sample if requested
            if samples_per_invoice and len(pairs) > samples_per_invoice:
                pairs = random.sample(pairs, samples_per_invoice)
            
            all_training_data.extend(pairs)
            
        except Exception as e:
            logger.error(f"Error processing {entry.get('invoice_id', 'unknown')}: {e}")
            continue
    
    # Save to JSONL file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in all_training_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    # Print statistics
    instruction_type_counts = {}
    for item in all_training_data:
        inst_type = item.get('instruction_type', 'unknown')
        instruction_type_counts[inst_type] = instruction_type_counts.get(inst_type, 0) + 1
    
    logger.info(f"\n✓ Created {len(all_training_data)} semantic instruction pairs")
    logger.info(f"✓ Saved to: {output_file}")
    logger.info(f"✓ Processed {len(manifest)} invoices")
    logger.info(f"\nInstruction Type Distribution:")
    for inst_type, count in sorted(instruction_type_counts.items()):
        logger.info(f"  {inst_type}: {count}")
    
    return len(all_training_data)


def process_directory(ground_truth_dir: str, images_dir: str, output_path: str,
                      include_types: Optional[List[str]] = None) -> int:
    """
    Process all metadata files in a directory.
    
    Args:
        ground_truth_dir: Directory containing JSON metadata files
        images_dir: Directory containing invoice images
        output_path: Path to output JSONL file
        include_types: Instruction types to include (None = all)
    
    Returns:
        Number of instruction pairs created
    """
    gt_dir = Path(ground_truth_dir)
    img_dir = Path(images_dir)
    
    all_training_data = []
    metadata_files = list(gt_dir.glob("*.json"))
    
    for metadata_file in tqdm(metadata_files, desc="Creating semantic instruction pairs"):
        try:
            # Find corresponding image
            invoice_id = metadata_file.stem
            image_file = None
            
            for pattern in [f"{invoice_id}.png", f"{invoice_id}.jpg", f"{invoice_id}_page_1.png"]:
                candidate = img_dir / pattern
                if candidate.exists():
                    image_file = candidate
                    break
            
            if image_file is None:
                # Try subdirectories
                for subdir in img_dir.iterdir():
                    if subdir.is_dir():
                        for pattern in [f"{invoice_id}.png", f"{invoice_id}_page_1.png"]:
                            candidate = subdir / pattern
                            if candidate.exists():
                                image_file = candidate
                                break
                    if image_file:
                        break
            
            if image_file is None:
                logger.warning(f"No image found for {invoice_id}")
                continue
            
            # Create instruction pairs
            pairs = create_semantic_instruction_pairs(
                str(metadata_file), 
                str(image_file),
                include_types=include_types
            )
            all_training_data.extend(pairs)
            
        except Exception as e:
            logger.error(f"Error processing {metadata_file.name}: {e}")
            continue
    
    # Save to JSONL file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in all_training_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    logger.info(f"\n✓ Created {len(all_training_data)} semantic instruction pairs")
    logger.info(f"✓ Saved to: {output_file}")
    logger.info(f"✓ Processed {len(metadata_files)} invoices")
    
    return len(all_training_data)


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create semantic instruction-response pairs for PaddleOCR-VL fine-tuning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all instruction types from manifest
  python create_semantic_instruction_pairs.py --manifest training_manifest.json --output semantic_data.jsonl
  
  # Generate only specific instruction types
  python create_semantic_instruction_pairs.py --manifest training_manifest.json \\
      --output semantic_data.jsonl --include-types field_extraction full_json_parsing
  
  # Limit samples per invoice (useful for large datasets)
  python create_semantic_instruction_pairs.py --manifest training_manifest.json \\
      --output semantic_data.jsonl --samples-per-invoice 5
        """
    )
    parser.add_argument(
        "--manifest",
        type=str,
        help="Path to training_manifest.json from synthetic invoice generator"
    )
    parser.add_argument(
        "--ground-truth-dir",
        type=str,
        help="Directory containing ground truth JSON files (alternative to --manifest)"
    )
    parser.add_argument(
        "--images-dir",
        type=str,
        help="Directory containing invoice images (required if using --ground-truth-dir)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="semantic_instruction_pairs.jsonl",
        help="Output JSONL file path (default: semantic_instruction_pairs.jsonl)"
    )
    parser.add_argument(
        "--include-types",
        nargs="+",
        choices=["field_extraction", "full_json_parsing", "table_reconstruction", 
                "logical_reasoning", "summarization"],
        help="Instruction types to include (default: all types)"
    )
    parser.add_argument(
        "--samples-per-invoice",
        type=int,
        help="Randomly sample this many pairs per invoice (useful for large datasets)"
    )
    
    args = parser.parse_args()
    
    if args.manifest:
        process_manifest(
            args.manifest, 
            args.output, 
            include_types=args.include_types,
            samples_per_invoice=args.samples_per_invoice
        )
    elif args.ground_truth_dir:
        if not args.images_dir:
            logger.error("Error: --images-dir is required when using --ground-truth-dir")
            sys.exit(1)
        process_directory(
            args.ground_truth_dir, 
            args.images_dir, 
            args.output,
            include_types=args.include_types
        )
    else:
        logger.error("Error: Either --manifest or --ground-truth-dir must be provided")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

