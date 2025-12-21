"""
Dataset generation pipeline for PaddleOCR-VL fine-tuning
Builds instruction-style datasets from cropped regions and annotations
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image
from tqdm import tqdm

from .formatters import (
    build_instruction_sample,
    format_vendor_block,
    format_line_items_table,
    format_totals_section,
)


def build_dataset(
    crops_dir: Path,
    annotations_dir: Path,
    region_types: List[str] = None,
) -> List[Dict[str, Any]]:
    """
    Builds a training dataset from cropped images and their annotations.
    
    Args:
        crops_dir: Directory containing cropped region images
        annotations_dir: Directory containing JSON annotation files
        region_types: Optional list of region types to include (None = all)
        
    Returns:
        List of instruction samples ready for training
    """
    if region_types is None:
        from .schema import REGION_TYPES
        region_types = REGION_TYPES
    
    dataset = []
    annotation_files = list(annotations_dir.glob("*.json"))
    
    for ann_file in tqdm(annotation_files, desc="Building dataset"):
        try:
            ann = json.loads(ann_file.read_text())
            
            # Get crop file path
            crop_file = ann.get("crop_file")
            if not crop_file:
                # Try to infer from annotation filename
                crop_file = ann_file.stem + ".png"
            
            crop_path = crops_dir / crop_file
            if not crop_path.exists():
                # Try other extensions
                for ext in [".jpg", ".jpeg", ".PNG", ".JPG"]:
                    alt_path = crops_dir / (ann_file.stem + ext)
                    if alt_path.exists():
                        crop_path = alt_path
                        break
                else:
                    continue
            
            # Load image
            try:
                image = Image.open(crop_path).convert("RGB")
            except Exception as e:
                print(f"Warning: Could not load image {crop_path}: {e}")
                continue
            
            # Get region type
            region_type = ann.get("region", ann.get("region_type", "vendor_block"))
            if region_type not in region_types:
                continue
            
            # Format target data based on region type
            target = ann.get("fields", ann.get("target", {}))
            
            if region_type == "vendor_block":
                target = format_vendor_block(target)
            elif region_type == "line_items_table":
                items = target.get("items", target.get("rows", target.get("line_items", [])))
                target = {"rows": format_line_items_table(items)}
            elif region_type == "totals_section":
                target = format_totals_section(target)
            # client_info and tax_section use target as-is
            
            # Build instruction sample
            sample = build_instruction_sample(
                image=image,
                region_type=region_type,
                target=target,
            )
            
            dataset.append(sample)
            
        except Exception as e:
            print(f"Error processing {ann_file}: {e}")
            continue
    
    return dataset


def build_dataset_from_manifest(
    manifest_path: Path,
    base_dir: Path = None,
) -> List[Dict[str, Any]]:
    """
    Builds dataset from a training manifest JSON file.
    
    Args:
        manifest_path: Path to training manifest JSON
        base_dir: Base directory for resolving relative paths
        
    Returns:
        List of instruction samples
    """
    if base_dir is None:
        base_dir = manifest_path.parent
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    dataset = []
    
    for entry in tqdm(manifest, desc="Processing manifest"):
        try:
            # Get paths
            image_path = Path(entry.get("image_path", ""))
            if not image_path.is_absolute():
                image_path = base_dir / image_path
            
            metadata_path = Path(entry.get("ground_truth_path", ""))
            if not metadata_path.is_absolute():
                metadata_path = base_dir / metadata_path
            
            if not image_path.exists() or not metadata_path.exists():
                continue
            
            # Load metadata
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Generate samples for each semantic region
            # This assumes we have a way to crop regions from the full invoice
            # For now, we'll create samples from the full image with region-specific prompts
            
            # Vendor block
            if "vendor" in data:
                vendor_image = Image.open(image_path).convert("RGB")
                vendor_target = format_vendor_block(data["vendor"])
                sample = build_instruction_sample(
                    image=vendor_image,
                    region_type="vendor_block",
                    target=vendor_target,
                )
                dataset.append(sample)
            
            # Line items table
            if "items" in data and data["items"]:
                items_image = Image.open(image_path).convert("RGB")
                items_target = {"rows": format_line_items_table(data["items"])}
                sample = build_instruction_sample(
                    image=items_image,
                    region_type="line_items_table",
                    target=items_target,
                )
                dataset.append(sample)
            
            # Totals section
            totals_data = {
                "subtotal": data.get("subtotal", 0.0),
                "tax_total": data.get("tax_total", 0.0),
                "discount_total": data.get("discount_total", 0.0),
                "grand_total": data.get("grand_total", 0.0),
                "currency": data.get("currency", "USD"),
            }
            totals_image = Image.open(image_path).convert("RGB")
            totals_target = format_totals_section(totals_data)
            sample = build_instruction_sample(
                image=totals_image,
                region_type="totals_section",
                target=totals_target,
            )
            dataset.append(sample)
            
        except Exception as e:
            print(f"Error processing manifest entry: {e}")
            continue
    
    return dataset


