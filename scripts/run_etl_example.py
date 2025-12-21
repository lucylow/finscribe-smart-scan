#!/usr/bin/env python3
"""
Example script demonstrating the complete ETL pipeline.

Usage:
    python scripts/run_etl_example.py examples/sample_invoice_1.png
"""
import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_pipeline.ingestion import ingest_from_local
from data_pipeline.preprocess import preprocess
from data_pipeline.ocr_client import run_ocr
from data_pipeline.semantic_parser import parse
from data_pipeline.normalizer import normalize_invoice_data
from data_pipeline.validator import validate
from data_pipeline.persistence import save_invoice


def main():
    """Run complete ETL pipeline on an invoice file."""
    if len(sys.argv) < 2:
        print("Usage: python run_etl_example.py <invoice_path>")
        print("Example: python run_etl_example.py examples/sample_invoice_1.png")
        sys.exit(1)
    
    invoice_path = sys.argv[1]
    
    if not os.path.exists(invoice_path):
        print(f"Error: File not found: {invoice_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("FinScribe ETL Pipeline - Example")
    print("=" * 60)
    print(f"Processing: {invoice_path}\n")
    
    try:
        # Extract
        print("[1/6] Ingesting file...")
        src = ingest_from_local(invoice_path)
        print(f"      ✓ Saved to: {src}")
        
        print("\n[2/6] Preprocessing image...")
        clean = preprocess(src)
        print(f"      ✓ Preprocessed: {clean}")
        
        print("\n[3/6] Running OCR...")
        ocr_result = run_ocr(clean)
        print(f"      ✓ OCR complete (confidence: {ocr_result.get('confidence', 0.0):.2f})")
        
        print("\n[4/6] Parsing semantic structure...")
        parsed = parse(ocr_result)
        print(f"      ✓ Extracted invoice number: {parsed.get('invoice_number', 'N/A')}")
        
        print("\n[5/6] Normalizing data...")
        normalized = normalize_invoice_data(parsed)
        print("      ✓ Normalization complete")
        
        print("\n[6/6] Validating...")
        validation = validate(normalized)
        if validation["ok"]:
            print("      ✓ Validation PASSED")
        else:
            print(f"      ✗ Validation FAILED: {validation['errors']}")
        
        # Optionally save to database
        save_to_db = os.getenv("SAVE_TO_DB", "false").lower() == "true"
        if save_to_db:
            print("\n[Saving to database...]")
            try:
                invoice_id = save_invoice(normalized, ocr_result, src)
                print(f"      ✓ Saved as invoice ID: {invoice_id}")
            except Exception as e:
                print(f"      ✗ Database save failed: {e}")
        else:
            print("\n[Database save skipped (set SAVE_TO_DB=true to enable)]")
        
        # Print results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print("\nStructured Data:")
        print(json.dumps(normalized, indent=2))
        
        print("\n" + "=" * 60)
        print("✅ ETL Pipeline Complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

