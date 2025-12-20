#!/usr/bin/env python3
"""
Phase 2: Training Data Preparation - Creating Instruction-Response Pairs

This script converts synthetic invoice metadata from Phase 1 into instruction-response
pairs for Supervised Fine-Tuning (SFT) of PaddleOCR-VL.

Each invoice generates multiple (prompt, response) pairs focusing on the 5 key semantic regions:
1. Vendor Block
2. Client/Invoice Info
3. Line Item Table
4. Tax & Discount Section
5. Grand Total & Payment Terms
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
from tqdm import tqdm


def create_instruction_pairs(metadata_path: str, image_path: str) -> List[Dict[str, Any]]:
    """
    Converts a single invoice's metadata into multiple instruction-response pairs.
    Each pair focuses on one of the 5 semantic regions.
    
    Args:
        metadata_path: Path to the JSON metadata file
        image_path: Path to the invoice image file
        
    Returns:
        List of instruction-response pair dictionaries
    """
    with open(metadata_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pairs = []
    invoice_id = data['invoice_id']
    
    # Pair 1: Extract Vendor Block
    vendor_prompt = "<image>\nExtract the vendor information from this invoice."
    vendor_response = json.dumps({
        "region": "vendor_block",
        "content": {
            "name": data['vendor']['name'],
            "address": f"{data['vendor']['address']}, {data['vendor']['city']}, {data['vendor']['country']} {data['vendor']['postal_code']}",
            "contact": f"Phone: {data['vendor']['phone']}, Email: {data['vendor']['email']}, Tax ID: {data['vendor']['tax_id']}"
        }
    }, ensure_ascii=False)
    pairs.append({
        "image": image_path,
        "conversations": [
            {"role": "human", "content": vendor_prompt},
            {"role": "assistant", "content": vendor_response}
        ]
    })
    
    # Pair 2: Extract Client & Invoice Metadata
    info_prompt = "<image>\nWhat is the invoice number, date, and due date?"
    info_response = json.dumps({
        "region": "client_invoice_info",
        "content": {
            "invoice_number": invoice_id,
            "issue_date": data['issue_date'],
            "due_date": data['due_date'],
            "client": data['client']['name']
        }
    }, ensure_ascii=False)
    pairs.append({
        "image": image_path,
        "conversations": [
            {"role": "human", "content": info_prompt},
            {"role": "assistant", "content": info_response}
        ]
    })
    
    # Pair 3: Extract Line Item Table
    # This is the most complex and important pair.
    table_prompt = "<image>\nParse the line item table into a structured JSON array."
    table_items = []
    for item in data['items']:
        # Calculate total if not present (for backward compatibility)
        item_total = item.get('total')
        if item_total is None:
            subtotal = item['quantity'] * item['unit_price']
            tax_amount = subtotal * (item.get('tax_rate', 0.0) / 100)
            item_total = subtotal + tax_amount - item.get('discount', 0.0)
        
        table_items.append({
            "description": item['description'],
            "quantity": item['quantity'],
            "unit_price": item['unit_price'],
            "line_total": round(item_total, 2)
        })
    table_response = json.dumps({
        "region": "line_item_table",
        "content": table_items
    }, ensure_ascii=False)
    pairs.append({
        "image": image_path,
        "conversations": [
            {"role": "human", "content": table_prompt},
            {"role": "assistant", "content": table_response}
        ]
    })
    
    # Pair 4 & 5: Tax, Discount, Grand Total, and Terms
    # Combined into financial summary
    totals_prompt = "<image>\nExtract the financial summary: subtotal, taxes, discounts, grand total, and payment terms."
    totals_response = json.dumps({
        "region": "financial_summary",
        "content": {
            "subtotal": data['subtotal'],
            "tax_total": data['tax_total'],
            "discount_total": data.get('discount_total', 0.0),
            "grand_total": data['grand_total'],
            "payment_terms": data['payment_terms'],
            "currency": data['currency']
        }
    }, ensure_ascii=False)
    pairs.append({
        "image": image_path,
        "conversations": [
            {"role": "human", "content": totals_prompt},
            {"role": "assistant", "content": totals_response}
        ]
    })
    
    return pairs


def process_manifest(manifest_path: str, output_path: str, base_dir: Path = None) -> int:
    """
    Process training manifest and create instruction pairs for all invoices.
    
    Args:
        manifest_path: Path to training_manifest.json from Phase 1
        output_path: Path to output JSONL file
        base_dir: Base directory for resolving relative paths (optional)
        
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
    for entry in tqdm(manifest, desc="Creating instruction pairs"):
        try:
            # Resolve paths relative to manifest location
            metadata_file = base_dir / Path(entry['ground_truth_path']).name
            if not metadata_file.exists():
                # Try with full path from manifest
                metadata_file = Path(entry['ground_truth_path'])
                if not metadata_file.is_absolute():
                    metadata_file = base_dir / metadata_file
            
            image_file = Path(entry['image_path'])
            if not image_file.is_absolute():
                image_file = base_dir / image_file
            
            # Verify files exist
            if not metadata_file.exists():
                print(f"Warning: Metadata file not found: {metadata_file}")
                continue
            if not image_file.exists():
                print(f"Warning: Image file not found: {image_file}")
                continue
            
            # Create instruction pairs
            pairs = create_instruction_pairs(str(metadata_file), str(image_file))
            all_training_data.extend(pairs)
            
        except Exception as e:
            print(f"Error processing {entry.get('invoice_id', 'unknown')}: {e}")
            continue
    
    # Save to JSONL file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in all_training_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"\n✓ Created {len(all_training_data)} instruction pairs")
    print(f"✓ Saved to: {output_file}")
    print(f"✓ Processed {len(manifest)} invoices")
    
    return len(all_training_data)


def process_directory(ground_truth_dir: str, images_dir: str, output_path: str) -> int:
    """
    Process all metadata files in a directory (alternative to manifest-based processing).
    
    Args:
        ground_truth_dir: Directory containing JSON metadata files
        images_dir: Directory containing invoice images
        output_path: Path to output JSONL file
        
    Returns:
        Number of instruction pairs created
    """
    gt_dir = Path(ground_truth_dir)
    img_dir = Path(images_dir)
    
    all_training_data = []
    metadata_files = list(gt_dir.glob("*.json"))
    
    for metadata_file in tqdm(metadata_files, desc="Creating instruction pairs"):
        try:
            # Try to find corresponding image file
            invoice_id = metadata_file.stem
            # Common image naming patterns
            image_file = None
            for pattern in [f"{invoice_id}.png", f"{invoice_id}.jpg", f"{invoice_id}_page_1.png"]:
                candidate = img_dir / pattern
                if candidate.exists():
                    image_file = candidate
                    break
            
            # If not found, try subdirectories
            if image_file is None:
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
                print(f"Warning: No image found for {invoice_id}")
                continue
            
            # Create instruction pairs
            pairs = create_instruction_pairs(str(metadata_file), str(image_file))
            all_training_data.extend(pairs)
            
        except Exception as e:
            print(f"Error processing {metadata_file.name}: {e}")
            continue
    
    # Save to JSONL file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in all_training_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"\n✓ Created {len(all_training_data)} instruction pairs")
    print(f"✓ Saved to: {output_file}")
    print(f"✓ Processed {len(metadata_files)} invoices")
    
    return len(all_training_data)


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create instruction-response pairs from Phase 1 synthetic invoice data"
    )
    parser.add_argument(
        "--manifest",
        type=str,
        help="Path to training_manifest.json from Phase 1"
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
        default="paddleocr_finetune_data.jsonl",
        help="Output JSONL file path (default: paddleocr_finetune_data.jsonl)"
    )
    
    args = parser.parse_args()
    
    if args.manifest:
        # Process using manifest
        base_dir = Path(args.manifest).parent
        process_manifest(args.manifest, args.output, base_dir)
    elif args.ground_truth_dir:
        # Process using directory
        if not args.images_dir:
            print("Error: --images-dir is required when using --ground-truth-dir")
            sys.exit(1)
        process_directory(args.ground_truth_dir, args.images_dir, args.output)
    else:
        print("Error: Either --manifest or --ground-truth-dir must be provided")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

