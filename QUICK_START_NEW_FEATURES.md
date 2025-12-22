# Quick Start: New FinScribe Features

This guide shows you how to quickly use the new production-grade features.

## 🚀 Quick Examples

### 1. Parse an Invoice with Semantic Parsing

```python
from finscribe.semantic_invoice_parser import parse_ocr_artifact_to_structured

# Your OCR artifact (from PaddleOCR)
ocr_artifact = {
    "regions": [
        {"text": "Invoice #INV-1234", "bbox": [10, 10, 200, 20], "confidence": 0.98},
        {"text": "Total $108.00", "bbox": [10, 500, 150, 20], "confidence": 0.96},
    ]
}

# Parse it
structured = parse_ocr_artifact_to_structured(ocr_artifact)
print(structured["invoice_number"])  # "INV-1234"
print(structured["financial_summary"]["total"])  # 108.00
```

### 2. Process a PDF (Multi-Page)

```python
from finscribe.pdf_utils import split_pdf_to_images

# Read PDF
with open("invoice.pdf", "rb") as f:
    pdf_bytes = f.read()

# Split into pages
pages = split_pdf_to_images(pdf_bytes, dpi=200)

# Process each page
for i, page_bytes in enumerate(pages):
    # Run OCR on each page
    ocr_result = ocr_client.analyze_image_bytes(page_bytes)
    # Process further...
```

### 3. Visualize OCR Results

```python
from finscribe.visualize import draw_ocr_overlay, image_to_bytes

# Create overlay with bounding boxes
overlay_img = draw_ocr_overlay(image_bytes, ocr_regions, show_confidence=True)

# Save it
overlay_bytes = image_to_bytes(overlay_img)
with open("output_overlay.png", "wb") as f:
    f.write(overlay_bytes)
```

### 4. Use Schema-Aware Routing

```python
from finscribe.schemas import infer_doc_type, get_schema_for_doc_type
from finscribe.schema_router import extract_fields_by_schema

# Auto-detect document type
doc_text = " ".join(r["text"] for r in ocr_regions)
doc_type = infer_doc_type(doc_text)  # "invoice", "receipt", etc.

# Get schema and extract fields
schema = get_schema_for_doc_type(doc_type)
fields = extract_fields_by_schema(ocr_regions, schema)
```

### 5. Aggregate with Confidence Weighting

```python
from finscribe.confidence import aggregate_invoice_totals

# Aggregate totals from multiple regions
total, confidence = aggregate_invoice_totals(ocr_regions)
print(f"Total: ${total} (confidence: {confidence:.2f})")
```

### 6. Log Data for Fine-Tuning

```python
from training.finetune_hooks import get_finetune_hooks

hooks = get_finetune_hooks()

# Log low-confidence samples (automatically collected for training)
hooks.log_low_confidence_ocr(ocr_artifact, confidence_threshold=0.7)

# Log validation failures
hooks.log_validation_failure(ocr_artifact, structured_output, validation_result)
```

## 📦 Installation

Most dependencies are already in `requirements.txt`. For PDF support:

```bash
pip install pdf2image

# Also install poppler-utils:
# macOS: brew install poppler
# Ubuntu/Debian: sudo apt-get install poppler-utils
```

## 🧪 Run Tests

```bash
pytest tests/test_semantic_parse.py
pytest tests/test_confidence_aggregation.py
```

## 📚 Full Documentation

See `FEATURES_IMPLEMENTATION.md` for detailed documentation of all features.

## 🎯 Integration Example

See `finscribe/integration_example.py` for a complete example combining all features.

