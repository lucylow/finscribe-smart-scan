"""
Example script for generating synthetic receipts for training.
"""

from pathlib import Path
from finscribe.receipts import SyntheticReceiptGenerator

def main():
    """Generate a sample receipt dataset"""
    
    # Initialize generator
    config_path = "app/config/receipt_config.yaml"
    generator = SyntheticReceiptGenerator(config_path=config_path)
    
    # Generate a small dataset for testing
    print("Generating synthetic receipt dataset...")
    dataset = generator.generate_dataset(
        num_receipts=100,  # Start with 100 for testing
        output_dir="./receipt_dataset"
    )
    
    print(f"\n✅ Generated {len(dataset)} receipts successfully!")
    print(f"📁 Dataset location: ./receipt_dataset")
    print(f"   - Images: ./receipt_dataset/images/")
    print(f"   - Labels: ./receipt_dataset/labels/")
    print(f"   - Manifest: ./receipt_dataset/dataset_manifest.json")
    
    # Show sample receipt info
    if dataset:
        sample = dataset[0]
        print(f"\n📋 Sample Receipt:")
        print(f"   Type: {sample['receipt_type']}")
        print(f"   Merchant: {sample['metadata']['merchant_name']}")
        print(f"   Items: {len(sample['metadata']['items'])}")
        print(f"   Total: ${sample['metadata']['total_paid']:.2f}")
    
    print("\n💡 Next steps:")
    print("   1. Review generated receipts in ./receipt_dataset/images/")
    print("   2. Use the dataset for fine-tuning: python -m finscribe.receipts.finetune --dataset_path ./receipt_dataset")
    print("   3. Or process receipts directly through the API")

if __name__ == "__main__":
    main()

