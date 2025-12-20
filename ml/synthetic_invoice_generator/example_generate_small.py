#!/usr/bin/env python3
"""
Example script to generate a small test dataset (10 invoices)
Useful for testing the system before generating the full dataset
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.data_generator import SyntheticInvoiceGenerator
import yaml


def main():
    """Generate a small test dataset"""
    
    print("Generating test dataset (10 invoices)...")
    
    # Load config
    config_path = Path(__file__).parent / "config" / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Override for test
    config['generation']['num_invoices'] = 10
    config['generation']['batch_size'] = 10
    config['augmentation']['apply_augmentation'] = False  # Skip augmentation for speed
    
    # Save temporary config
    temp_config_path = Path(__file__).parent / "config" / "config_test.yaml"
    with open(temp_config_path, 'w') as f:
        yaml.dump(config, f)
    
    # Initialize generator with test config
    generator = SyntheticInvoiceGenerator(config_path=str(temp_config_path))
    
    # Generate invoices
    all_metadata = generator.generate_batch(start_id=1, batch_size=10)
    
    print(f"\n✓ Test dataset generated!")
    print(f"✓ Generated {len(all_metadata)} invoices")
    print(f"✓ Output directory: {generator.config['generation']['output_dir']}")
    
    # Clean up temp config
    temp_config_path.unlink()
    
    if all_metadata:
        sample = all_metadata[0]['metadata']
        print(f"\nSample invoice:")
        print(f"  ID: {sample['invoice_id']}")
        print(f"  Vendor: {sample['vendor']['name']}")
        print(f"  Total: {sample['currency']} {sample['grand_total']:.2f}")


if __name__ == "__main__":
    main()

