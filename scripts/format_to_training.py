#!/usr/bin/env python3
"""
Convert annotations.jsonl to instruction-target pairs for SFT.
Output: data/training/train.jsonl and val.jsonl where each line:
{ "image": "data/dataset/images/...", "prompt": "<instruction>", "response": "<json-string>" }
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
IN = ROOT / "data" / "dataset"
OUT = ROOT / "data" / "training"
OUT.mkdir(parents=True, exist_ok=True)

def make_prompt(ann):
    """Generate instruction prompt for PaddleOCR-VL SFT"""
    # For PaddleOCR-VL SFT we will use a simple instruction:
    return "Extract structured financial fields (vendor, invoice_number, line_items, financial_summary) as JSON."

def ann_to_pair(ann):
    """Convert annotation to training pair"""
    prompt = make_prompt(ann)
    # response is the ground truth JSON
    # Use relative path from ROOT
    image_path = ann["image_path"]
    if not os.path.isabs(image_path):
        # Already relative
        image_rel = image_path
    else:
        # Make relative to ROOT
        try:
            image_rel = os.path.relpath(image_path, ROOT)
        except Exception:
            image_rel = image_path
    
    response = json.dumps(ann["fields"], ensure_ascii=False)
    return {"image": image_rel, "prompt": prompt, "response": response}

for split in ["train", "val", "test"]:
    in_file = IN / f"{split}.jsonl"
    out_file = OUT / f"{split}.jsonl"
    if not in_file.exists():
        print(f"Warning: {in_file} does not exist, skipping")
        continue
    with open(out_file, "w", encoding="utf8") as outfh:
        with open(in_file, "r", encoding="utf8") as infh:
            count = 0
            for line in infh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ann = json.loads(line)
                    pair = ann_to_pair(ann)
                    outfh.write(json.dumps(pair, ensure_ascii=False) + "\n")
                    count += 1
                except Exception as e:
                    print(f"Warning: skipping invalid line in {in_file}: {e}")
                    continue
    print(f"Wrote {count} training pairs to {out_file}")

