#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.pipeline.ocr_pipeline import run_full_pipeline

if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[1]
    img = repo / "examples" / "Walmartreceipt.jpeg"
    if not img.exists():
        print("examples/Walmartreceipt.jpeg not found — using built-in mock.")
        img = repo / "examples" / "sample1.jpg"
        if not img.exists():
            print("examples/sample1.jpg not found — pipeline will use mock data.")
            img = "examples/sample1.jpg"  # Will trigger mock
    res = run_full_pipeline(str(img) if isinstance(img, Path) and img.exists() else str(repo / "examples" / "sample1.jpg"), use_ernie=False)
    print(json.dumps(res, indent=2, ensure_ascii=False))

