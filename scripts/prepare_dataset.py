#!/usr/bin/env python3
"""
scripts/prepare_dataset.py

Scan `examples/` and `data/synthetic/` (if present) and produce:
- data/dataset/annotations.jsonl  (one JSON per line)
- data/dataset/images/  (symlink or copy)
Also create train/val/test splits: train=80%, val=10%, test=10%
Configuration: adjust paths at top if needed.
"""
import os
import json
import random
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
EXAMPLES = ROOT / "examples"
SYNTH = ROOT / "data" / "synthetic"
DATA_SYNTH = ROOT / "data" / "synth"  # alternative path
OUT = ROOT / "data" / "dataset"
OUT_IMAGES = OUT / "images"
OUT.mkdir(parents=True, exist_ok=True)
OUT_IMAGES.mkdir(parents=True, exist_ok=True)

def load_annotation_from_json(json_path):
    """Load ground truth JSON annotation file"""
    try:
        with open(json_path, "r", encoding="utf8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: could not load {json_path}: {e}")
        return None

def find_image_for_annotation(ann_path, base_dir):
    """Find corresponding image file for an annotation"""
    # Try common image extensions
    base = ann_path.stem
    for ext in [".png", ".jpg", ".jpeg", ".tiff", ".pdf"]:
        img_path = ann_path.parent / f"{base}{ext}"
        if img_path.exists():
            return img_path
        # Also check images subdirectory
        img_path = ann_path.parent.parent / "images" / f"{base}{ext}"
        if img_path.exists():
            return img_path
    return None

# Collect image files and their annotations
imgs = []
annotations = []

# 1. Check data/synthetic/ or data/synth/ directories (from generate_synthetic_invoices.py)
for synth_dir in [SYNTH, DATA_SYNTH]:
    if not synth_dir.exists():
        continue
    
    # Look for ground_truth directory with JSON files
    gt_dir = synth_dir / "ground_truth"
    images_dir = synth_dir / "images"
    
    if gt_dir.exists():
        for json_file in gt_dir.glob("*.json"):
            ann = load_annotation_from_json(json_file)
            if ann is None:
                continue
            
            # Find corresponding image
            img_path = find_image_for_annotation(json_file, synth_dir)
            if img_path is None:
                # Try images directory with same filename
                for ext in [".png", ".jpg", ".jpeg"]:
                    candidate = images_dir / f"{json_file.stem}{ext}"
                    if candidate.exists():
                        img_path = candidate
                        break
            
            if img_path and img_path.exists():
                imgs.append((img_path, ann, json_file))
    
    # Also collect images directly if no ground_truth directory
    if images_dir.exists():
        for img_file in images_dir.glob("*"):
            if img_file.suffix.lower() in [".png", ".jpg", ".jpeg", ".tiff"]:
                # Try to find corresponding JSON
                json_file = gt_dir / f"{img_file.stem}.json" if gt_dir.exists() else None
                if json_file and json_file.exists():
                    ann = load_annotation_from_json(json_file)
                else:
                    # Create minimal annotation from filename
                    ann = {
                        "invoice_id": img_file.stem,
                        "vendor": {"name": "Unknown Vendor"},
                        "client": {},
                        "line_items": [],
                        "financial_summary": {"subtotal": 0.0, "tax_rate": 0.0, "tax_amount": 0.0, "grand_total": 0.0}
                    }
                imgs.append((img_file, ann, json_file))

# 2. Check examples/ directory
if EXAMPLES.exists():
    for img_file in EXAMPLES.glob("**/*"):
        if img_file.suffix.lower() in [".png", ".jpg", ".jpeg", ".tiff"]:
            # Try to find corresponding JSON
            json_file = img_file.with_suffix(".json")
            if json_file.exists():
                ann = load_annotation_from_json(json_file)
            else:
                # Create minimal annotation
                ann = {
                    "invoice_id": img_file.stem,
                    "vendor": {"name": "Example Vendor"},
                    "client": {},
                    "line_items": [],
                    "financial_summary": {"subtotal": 0.0, "tax_rate": 0.0, "tax_amount": 0.0, "grand_total": 0.0}
                }
            if ann:
                imgs.append((img_file, ann, json_file))

print(f"Found {len(imgs)} image-annotation pairs")

# Process and copy images, create annotations
for i, (img_path, ann_dict, json_file) in enumerate(sorted(imgs)):
    # Copy image to dataset/images
    dst = OUT_IMAGES / f"img_{i:05d}{img_path.suffix}"
    try:
        shutil.copy(img_path, dst)
    except Exception as e:
        # fallback to symlink when copy fails
        try:
            if dst.exists():
                dst.unlink()
            os.symlink(os.path.abspath(img_path), dst)
        except Exception as e2:
            print(f"Warning: could not copy/link {img_path}: {e2}")
            continue

    # Normalize annotation format
    # Convert existing format to standardized format
    standardized = {
        "image_path": str(dst.relative_to(ROOT)),
        "fields": {},
        "tables": [],
        "metadata": {"source": str(img_path.relative_to(ROOT)) if img_path.is_relative_to(ROOT) else str(img_path)}
    }
    
    # Extract fields from annotation dict
    if "vendor" in ann_dict:
        if isinstance(ann_dict["vendor"], dict):
            standardized["fields"]["vendor"] = ann_dict["vendor"]
        else:
            standardized["fields"]["vendor"] = {"name": str(ann_dict["vendor"])}
    
    # Extract invoice_number
    invoice_id = ann_dict.get("invoice_id") or ann_dict.get("invoice_number") or img_path.stem
    standardized["fields"]["invoice_number"] = str(invoice_id)
    
    # Extract line_items
    if "line_items" in ann_dict:
        standardized["fields"]["line_items"] = ann_dict["line_items"]
    elif "items" in ann_dict:
        # Convert items format to line_items
        items = []
        for item in ann_dict["items"]:
            items.append({
                "desc": item.get("description") or item.get("desc", ""),
                "qty": item.get("quantity") or item.get("qty", 1),
                "unit_price": float(item.get("unit_price") or item.get("price", 0.0)),
                "line_total": float(item.get("line_total") or item.get("total") or item.get("subtotal", 0.0))
            })
        standardized["fields"]["line_items"] = items
    
    # Extract financial_summary
    if "financial_summary" in ann_dict:
        standardized["fields"]["financial_summary"] = ann_dict["financial_summary"]
    elif "subtotal" in ann_dict or "grand_total" in ann_dict:
        # Build from top-level fields
        fin = {
            "subtotal": float(ann_dict.get("subtotal", 0.0)),
            "tax_rate": float(ann_dict.get("tax_rate", ann_dict.get("metadata", {}).get("tax_rate", 0.0))),
            "tax_amount": float(ann_dict.get("tax_amount", ann_dict.get("tax_total", 0.0))),
            "grand_total": float(ann_dict.get("grand_total", ann_dict.get("total", 0.0)))
        }
        standardized["fields"]["financial_summary"] = fin
    else:
        # Calculate from line_items
        line_items = standardized["fields"].get("line_items", [])
        subtotal = sum(float(item.get("line_total", 0.0)) for item in line_items)
        tax_rate = 0.1  # default
        tax_amount = subtotal * tax_rate
        grand_total = subtotal + tax_amount
        standardized["fields"]["financial_summary"] = {
            "subtotal": subtotal,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "grand_total": grand_total
        }
    
    # Extract client if present
    if "client" in ann_dict:
        standardized["fields"]["client"] = ann_dict["client"]
    
    annotations.append(standardized)

# Create splits
random.seed(42)
random.shuffle(annotations)
n = len(annotations)
train_cut = int(n * 0.8)
val_cut = int(n * 0.9)

# Write full annotations
with open(OUT / "annotations.jsonl", "w", encoding="utf8") as fh:
    for ann in annotations:
        fh.write(json.dumps(ann, ensure_ascii=False) + "\n")

# Write split files
for name, subset in [
    ("train", annotations[:train_cut]),
    ("val", annotations[train_cut:val_cut]),
    ("test", annotations[val_cut:])
]:
    with open(OUT / f"{name}.jsonl", "w", encoding="utf8") as fh:
        for ann in subset:
            fh.write(json.dumps(ann, ensure_ascii=False) + "\n")

print(f"Wrote {len(annotations)} annotations")
print(f"  Train: {train_cut} samples")
print(f"  Val: {val_cut - train_cut} samples")
print(f"  Test: {n - val_cut} samples")
print(f"Output directory: {OUT}")

