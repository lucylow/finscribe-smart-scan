#!/usr/bin/env python3
"""
Example: Generate synthetic training data for PaddleOCR-VL fine-tuning
"""

from pathlib import Path
from finscribe.synthetic.export import generate_dataset

if __name__ == "__main__":
    # Generate 1000 synthetic invoices
    output_dir = Path("data/synthetic_invoices")
    
    print("Generating synthetic invoice dataset...")
    generate_dataset(
        num_samples=1000,
        output_dir=output_dir,
        prefix="invoice",
    )
    
    print(f"\n✓ Generated dataset in {output_dir}")
    print(f"✓ Created training_manifest.json with {1000} samples")

