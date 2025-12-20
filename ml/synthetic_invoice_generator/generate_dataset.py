#!/usr/bin/env python3
"""
Main execution script for synthetic invoice dataset generation
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.data_generator import SyntheticInvoiceGenerator
from src.augmentation import DocumentAugmentor
from src.utils import PDFProcessor
import json


def main():
    """Main execution script for dataset generation"""
    
    print("=" * 60)
    print("Synthetic Invoice Dataset Generator")
    print("=" * 60)
    
    # Initialize generator
    print("\n1. Initializing generator...")
    config_path = Path(__file__).parent / "config" / "config.yaml"
    generator = SyntheticInvoiceGenerator(config_path=str(config_path))
    
    # Generate invoices
    print("\n2. Generating synthetic invoices...")
    all_metadata = generator.generate_full_dataset()
    
    # Convert PDFs to images
    print("\n3. Converting PDFs to training images...")
    # Resolve output_dir relative to script location
    output_dir_str = generator.config['generation']['output_dir']
    if not os.path.isabs(output_dir_str):
        base_dir = Path(__file__).parent
        output_dir = base_dir / output_dir_str
    else:
        output_dir = Path(output_dir_str)
    
    pdf_dir = output_dir / 'pdfs'
    image_dir = output_dir / 'images'
    gt_dir = output_dir / 'ground_truth'
    
    training_pairs = PDFProcessor.create_training_pairs(
        str(pdf_dir),
        str(gt_dir),
        str(image_dir)
    )
    
    # Apply augmentations if enabled
    if generator.config['augmentation']['apply_augmentation']:
        print("\n4. Applying realistic augmentations...")
        augmentor = DocumentAugmentor()
        augmented_dir = output_dir / 'augmented'
        augmented_dir.mkdir(parents=True, exist_ok=True)
        
        # Augment a subset of images for variation
        # You can adjust this ratio based on your needs
        augment_ratio = 0.2  # Augment 20% of images
        num_to_augment = max(1, int(len(training_pairs) * augment_ratio))
        images_to_augment = training_pairs[:num_to_augment]
        
        augmented_pairs = []
        for idx, pair in enumerate(images_to_augment):
            try:
                original_image = Path(pair['image_path'])
                augmented_path = augmented_dir / f"aug_{original_image.name}"
                
                augmentor.apply_random_augmentation_combination(
                    str(original_image),
                    str(augmented_path)
                )
                
                # Create new training pair for augmented image
                augmented_pair = pair.copy()
                augmented_pair['image_path'] = str(augmented_path)
                augmented_pair['is_augmented'] = True
                augmented_pairs.append(augmented_pair)
                
                if (idx + 1) % 50 == 0:
                    print(f"  Augmented {idx + 1}/{num_to_augment} images...")
            except Exception as e:
                print(f"  Warning: Could not augment {pair['image_path']}: {e}")
                continue
        
        # Combine original and augmented pairs
        training_pairs.extend(augmented_pairs)
        print(f"  Total augmented images created: {len(augmented_pairs)}")
    
    # Save training manifest
    print("\n5. Creating training manifest...")
    manifest_path = output_dir / 'training_manifest.json'
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(training_pairs, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Dataset generation complete!")
    print(f"✓ Total training samples: {len(training_pairs)}")
    print(f"✓ Manifest saved to: {manifest_path}")
    print(f"✓ Output directory: {output_dir}")
    
    # Print sample statistics
    print("\n" + "=" * 60)
    print("SAMPLE INVOICE GENERATED:")
    print("=" * 60)
    
    if all_metadata:
        sample = all_metadata[0]['metadata']
        print(f"Invoice ID: {sample['invoice_id']}")
        print(f"Vendor: {sample['vendor']['name']}")
        print(f"Client: {sample['client']['name']}")
        print(f"Items: {len(sample['items'])}")
        print(f"Total: {sample['currency']} {sample['grand_total']:.2f}")
        print(f"Layout: {sample['layout_type']}")
        print(f"Language: {sample['language']}")
    
    # Print summary statistics
    print("\n" + "=" * 60)
    print("DATASET STATISTICS:")
    print("=" * 60)
    
    augmented_count = sum(1 for p in training_pairs if p.get('is_augmented', False))
    original_count = len(training_pairs) - augmented_count
    
    print(f"Total images: {len(training_pairs)}")
    print(f"  - Original: {original_count}")
    print(f"  - Augmented: {augmented_count}")
    print(f"Total invoices: {len(all_metadata)}")
    
    languages = set(m['metadata']['language'] for m in all_metadata)
    currencies = set(m['metadata']['currency'] for m in all_metadata)
    layouts = set(m['metadata']['layout_type'] for m in all_metadata)
    
    print(f"Languages: {sorted(languages)}")
    print(f"Currencies: {sorted(currencies)}")
    print(f"Layouts: {sorted(layouts)}")


if __name__ == "__main__":
    main()

