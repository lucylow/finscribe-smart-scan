#!/usr/bin/env python3
"""
Example usage of Phase 2 fine-tuning components

This script demonstrates how to use the Phase 2 components:
1. Creating instruction pairs
2. Setting up training
3. Running evaluation
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from create_instruction_pairs import create_instruction_pairs, process_manifest
from evaluation_metrics import evaluate_sample, evaluate_dataset


def example_create_instruction_pairs():
    """Example: Create instruction pairs from a single invoice"""
    print("=" * 60)
    print("Example 1: Creating instruction pairs from single invoice")
    print("=" * 60)
    
    # Example paths (adjust to your actual data)
    metadata_path = "../synthetic_invoice_generator/output/ground_truth/INV-2024-000001.json"
    image_path = "../synthetic_invoice_generator/output/images/INV-2024-000001/INV-2024-000001_page_1.png"
    
    # Check if files exist
    if not Path(metadata_path).exists():
        print(f"Warning: Metadata file not found: {metadata_path}")
        print("Please adjust paths to point to your actual Phase 1 data")
        return
    
    # Create instruction pairs
    pairs = create_instruction_pairs(metadata_path, image_path)
    
    print(f"\nCreated {len(pairs)} instruction pairs:")
    for i, pair in enumerate(pairs, 1):
        prompt = pair['conversations'][0]['content']
        response = pair['conversations'][1]['content']
        
        # Parse response to show region
        try:
            response_dict = json.loads(response)
            region = response_dict.get('region', 'unknown')
        except:
            region = 'unknown'
        
        print(f"\nPair {i} - Region: {region}")
        print(f"  Prompt: {prompt[:80]}...")
        print(f"  Response: {response[:100]}...")


def example_process_manifest():
    """Example: Process entire manifest to create training dataset"""
    print("\n" + "=" * 60)
    print("Example 2: Processing training manifest")
    print("=" * 60)
    
    manifest_path = "../synthetic_invoice_generator/output/training_manifest.json"
    
    if not Path(manifest_path).exists():
        print(f"Warning: Manifest file not found: {manifest_path}")
        print("Run Phase 1 data generation first, or adjust the path")
        return
    
    output_path = "example_finetune_data.jsonl"
    base_dir = Path(manifest_path).parent
    
    print(f"Processing manifest: {manifest_path}")
    print(f"Output will be saved to: {output_path}")
    
    num_pairs = process_manifest(manifest_path, output_path, base_dir)
    
    print(f"\n✓ Successfully created {num_pairs} instruction pairs")


def example_evaluation():
    """Example: Evaluate model predictions"""
    print("\n" + "=" * 60)
    print("Example 3: Evaluating predictions")
    print("=" * 60)
    
    # Example ground truth
    ground_truth = {
        "invoice_id": "INV-2024-000001",
        "issue_date": "2024-01-15",
        "due_date": "2024-02-14",
        "currency": "USD",
        "vendor": {
            "name": "Acme Corporation",
            "address": "123 Main St",
            "city": "New York",
            "country": "USA",
            "postal_code": "10001",
            "phone": "+1-555-0100",
            "email": "contact@acme.com",
            "tax_id": "TAX123456"
        },
        "client": {
            "name": "Client Inc"
        },
        "items": [
            {
                "description": "Software License",
                "quantity": 2,
                "unit_price": 100.0,
                "total": 200.0
            }
        ],
        "subtotal": 200.0,
        "tax_total": 20.0,
        "discount_total": 0.0,
        "grand_total": 220.0,
        "payment_terms": "Net 30 days"
    }
    
    # Example prediction (correct)
    predicted_correct = json.dumps({
        "region": "vendor_block",
        "content": {
            "name": "Acme Corporation",
            "address": "123 Main St, New York, USA 10001",
            "contact": "Phone: +1-555-0100, Email: contact@acme.com, Tax ID: TAX123456"
        }
    })
    
    # Evaluate
    result = evaluate_sample(predicted_correct, ground_truth)
    
    print("Evaluation result for vendor_block:")
    print(f"  Accuracy: {result['field_extraction']['vendor_block']['overall_accuracy']:.2%}")
    print(f"  Field details: {result['field_extraction']['vendor_block']['field_details']}")
    
    # Example prediction (with error)
    predicted_error = json.dumps({
        "region": "financial_summary",
        "content": {
            "subtotal": 200.0,
            "tax_total": 20.0,
            "discount_total": 0.0,
            "grand_total": 250.0,  # Incorrect!
            "payment_terms": "Net 30 days",
            "currency": "USD"
        }
    })
    
    result2 = evaluate_sample(predicted_error, ground_truth)
    
    print("\nEvaluation result for financial_summary (with error):")
    print(f"  Accuracy: {result2['field_extraction']['financial_summary']['overall_accuracy']:.2%}")
    print(f"  Numerical validation valid: {result2['numerical_validation']['is_valid']}")
    if result2['numerical_validation']['errors']:
        print(f"  Errors: {result2['numerical_validation']['errors']}")


def main():
    """Run all examples"""
    print("Phase 2 Fine-Tuning - Example Usage")
    print("=" * 60)
    
    # Example 1: Single invoice instruction pairs
    example_create_instruction_pairs()
    
    # Example 2: Process manifest
    # Uncomment to run:
    # example_process_manifest()
    
    # Example 3: Evaluation
    example_evaluation()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run create_instruction_pairs.py on your Phase 1 data")
    print("2. Configure finetune_config.yaml")
    print("3. Run train_finetune.py to start training")
    print("4. Use evaluation_metrics.py to evaluate results")


if __name__ == "__main__":
    main()

