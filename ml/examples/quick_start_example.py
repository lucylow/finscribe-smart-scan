#!/usr/bin/env python3
"""
Quick Start Example - Generate a small test dataset
===================================================

This script demonstrates how to use the synthetic invoice generator
programmatically to create a small test dataset.
"""

from pathlib import Path
from synthetic_invoice_generator_example import generate_synthetic_invoices

if __name__ == '__main__':
    # Generate 10 test invoices
    print("Generating test dataset...")
    
    output_dir = Path('./test_invoices')
    
    generate_synthetic_invoices(
        count=10,
        output_dir=output_dir,
        layouts=['classic', 'modern'],
        locale='en_US'
    )
    
    print(f"\n✓ Test dataset ready in: {output_dir}")
    print(f"✓ Check the PDFs and annotations to verify quality")

