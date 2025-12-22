"""
Integration example showing how to use the new FinScribe features.

This demonstrates:
1. Invoice-specific semantic parsing
2. PDF page splitting
3. Schema-aware routing
4. Confidence-weighted aggregation
5. Visualization
6. Fine-tuning hooks
"""

import json
from typing import Dict, Any

# Import new modules
from finscribe.semantic_invoice_parser import parse_ocr_artifact_to_structured
from finscribe.pdf_utils import split_pdf_to_images
from finscribe.visualize import draw_ocr_overlay, image_to_bytes
from finscribe.confidence import aggregate_invoice_totals, aggregate_field_candidates
from finscribe.schemas import infer_doc_type, get_schema_for_doc_type
from finscribe.schema_router import group_regions_by_layout, extract_fields_by_schema
# Note: Fine-tuning hooks import (adjust path based on your project structure)
try:
    from training.finetune_hooks import get_finetune_hooks
except ImportError:
    # Fallback if training package not available
    def get_finetune_hooks():
        return None


def example_semantic_parsing(ocr_artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Example: Parse OCR artifact using invoice-specific heuristics."""
    structured = parse_ocr_artifact_to_structured(ocr_artifact)
    print(f"Extracted invoice: {structured['invoice_number']}")
    print(f"Total: {structured['financial_summary']['total']}")
    return structured


def example_pdf_processing(pdf_bytes: bytes) -> list:
    """Example: Split PDF into pages for processing."""
    pages = split_pdf_to_images(pdf_bytes, dpi=200)
    print(f"Split PDF into {len(pages)} pages")
    return pages


def example_schema_routing(regions: list, doc_text: str) -> Dict[str, Any]:
    """Example: Use schema-aware routing for field extraction."""
    # Auto-detect document type
    doc_type = infer_doc_type(doc_text)
    print(f"Detected document type: {doc_type}")
    
    # Get appropriate schema
    schema = get_schema_for_doc_type(doc_type)
    
    # Extract fields using schema
    extracted = extract_fields_by_schema(regions, schema)
    return extracted


def example_confidence_aggregation(regions: list) -> Dict[str, Any]:
    """Example: Use confidence-weighted aggregation."""
    # Aggregate invoice totals
    total, conf = aggregate_invoice_totals(regions)
    print(f"Aggregated total: ${total} (confidence: {conf:.2f})")
    
    # Aggregate other fields
    vendor_candidates = [
        {"value": r.get("text"), "confidence": r.get("confidence", 0.5)}
        for r in regions[:5]  # First few regions
    ]
    vendor_result = aggregate_field_candidates("vendor_name", vendor_candidates)
    print(f"Aggregated vendor: {vendor_result['value']} (confidence: {vendor_result['confidence']:.2f})")
    
    return {"total": total, "total_confidence": conf, "vendor": vendor_result}


def example_visualization(image_bytes: bytes, regions: list, output_path: str):
    """Example: Create OCR overlay visualization."""
    overlay_img = draw_ocr_overlay(image_bytes, regions, show_confidence=True, show_text=True)
    overlay_bytes = image_to_bytes(overlay_img)
    
    with open(output_path, "wb") as f:
        f.write(overlay_bytes)
    print(f"Saved visualization to {output_path}")


def example_finetuning_hooks(ocr_artifact: Dict[str, Any], structured_output: Dict[str, Any], validation_result: Dict[str, Any]):
    """Example: Log data for fine-tuning when confidence is low."""
    hooks = get_finetune_hooks()
    
    if hooks is None:
        print("Fine-tuning hooks not available")
        return
    
    # Log low confidence OCR
    hooks.log_low_confidence_ocr(ocr_artifact, confidence_threshold=0.7)
    
    # Log validation failures
    hooks.log_validation_failure(ocr_artifact, structured_output, validation_result)


def example_full_pipeline(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Full pipeline example combining all features.
    
    This demonstrates a complete workflow:
    1. Split PDF to pages
    2. Process each page with OCR
    3. Use semantic parsing
    4. Apply schema-aware routing
    5. Aggregate with confidence weighting
    6. Generate visualization
    7. Log for fine-tuning if needed
    """
    # Step 1: Split PDF
    pages = split_pdf_to_images(pdf_bytes)
    
    # Step 2: Process first page (in real pipeline, process all pages)
    if pages:
        # In real implementation, you'd run OCR here
        # For this example, assume we have OCR results
        ocr_artifact = {
            "regions": [
                {"text": "Invoice #INV-123", "bbox": [10, 10, 200, 20], "confidence": 0.95},
                {"text": "Total $100.00", "bbox": [10, 500, 150, 20], "confidence": 0.92},
            ]
        }
        
        # Step 3: Semantic parsing
        structured = parse_ocr_artifact_to_structured(ocr_artifact)
        
        # Step 4: Schema routing
        doc_text = " ".join(r["text"] for r in ocr_artifact["regions"])
        schema_extracted = example_schema_routing(ocr_artifact["regions"], doc_text)
        
        # Step 5: Confidence aggregation
        aggregated = example_confidence_aggregation(ocr_artifact["regions"])
        
        # Step 6: Visualization (would need actual image bytes)
        # example_visualization(pages[0], ocr_artifact["regions"], "output_overlay.png")
        
        return {
            "structured": structured,
            "schema_extracted": schema_extracted,
            "aggregated": aggregated,
            "pages_processed": len(pages)
        }
    
    return {}


if __name__ == "__main__":
    # Example usage
    print("FinScribe Integration Examples")
    print("=" * 50)
    
    # Example OCR artifact
    ocr_artifact = {
        "regions": [
            {"text": "ACME Corp", "bbox": [10, 10, 200, 20], "confidence": 0.98},
            {"text": "Invoice #INV-1234", "bbox": [300, 15, 180, 18], "confidence": 0.97},
            {"text": "Total $108.00", "bbox": [300, 500, 150, 25], "confidence": 0.96},
        ]
    }
    
    # Run examples
    structured = example_semantic_parsing(ocr_artifact)
    aggregated = example_confidence_aggregation(ocr_artifact["regions"])
    schema_result = example_schema_routing(ocr_artifact["regions"], "Invoice #INV-1234")
    
    print("\n" + "=" * 50)
    print("Examples completed!")

