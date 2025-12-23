#!/usr/bin/env python3
# scripts/process_walmart_receipt.py
"""
Demo script to process Walmart receipt image.

Runs the full pipeline on examples/Walmartreceipt.jpeg and prints JSON output.
"""
import os, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.pipeline.walmart_pipeline import run_walmart_pipeline

def main():
    repo_root = Path(__file__).resolve().parents[1]
    img = repo_root / "examples" / "Walmartreceipt.jpeg"
    if not img.exists():
        print("ERROR: examples/Walmartreceipt.jpeg not found. Please place the receipt there.")
        sys.exit(2)
    res = run_walmart_pipeline(str(img))
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()

