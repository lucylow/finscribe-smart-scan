"""
Export utilities for synthetic invoice generation
"""

import json
from pathlib import Path
from PIL import Image
from typing import Dict, Any, Tuple


def export_sample(
    image: Image.Image,
    data: Dict[str, Any],
    out_dir: Path,
    idx: int,
    prefix: str = "invoice",
) -> Tuple[Path, Path]:
    """
    Exports a synthetic invoice sample (image + metadata).
    
    Args:
        image: PIL Image of the invoice
        data: Invoice data dictionary
        out_dir: Output directory
        idx: Sample index
        
    Returns:
        Tuple of (image_path, metadata_path) - both Path objects
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Save image
    image_path = out_dir / f"{prefix}_{idx:06d}.png"
    image.save(image_path)
    
    # Save metadata
    metadata_path = out_dir / f"{prefix}_{idx:06d}.json"
    metadata_path.write_text(json.dumps(data, indent=2))
    
    return image_path, metadata_path


def generate_dataset(
    num_samples: int,
    output_dir: Path,
    prefix: str = "invoice",
) -> Path:
    """
    Generates a complete dataset of synthetic invoices.
    
    Args:
        num_samples: Number of invoices to generate
        output_dir: Output directory
        prefix: Filename prefix
        
    Returns:
        Path to the output directory
    """
    from .generator import generate_invoice
    from .renderer import render_invoice
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for idx in range(num_samples):
        # Generate invoice
        data = generate_invoice(
            include_tax=idx % 2 == 0,  # Alternate tax inclusion
            include_discount=idx % 3 == 0,  # Some with discounts
        )
        
        # Render image
        image = render_invoice(data)
        
        # Export
        export_sample(image, data, output_dir, idx, prefix)
    
    # Create manifest
    manifest = []
    for idx in range(num_samples):
        manifest.append({
            "invoice_id": f"{prefix}_{idx:06d}",
            "image_path": str(output_dir / f"{prefix}_{idx:06d}.png"),
            "ground_truth_path": str(output_dir / f"{prefix}_{idx:06d}.json"),
        })
    
    manifest_path = output_dir / "training_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    
    return output_dir

