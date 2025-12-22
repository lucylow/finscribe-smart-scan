# Finance Data Layer Implementation

## Overview

This is a production-grade Finance Data layer for FinScribe, focused on accuracy, auditability, retraining, and judge credibility. It provides:

- ✅ Canonical financial schema (robust, validated, extensible)
- ✅ Deterministic validation & reconciliation (math + business rules)
- ✅ ETL-ready storage (raw → parsed → validated → corrected)
- ✅ Active-learning–ready datasets (for OCR & LLM fine-tuning)

## Architecture

### 1. Canonical Financial Data Model (`app/models/finance.py`)

Pydantic models that serve as the single source of truth for all invoices/statements:

- `Money`: Monetary amount with currency (rounded to 2 decimal places)
- `Vendor`: Vendor/seller information
- `LineItem`: Individual invoice line item with automatic math validation
- `Invoice`: Complete invoice with automatic validation of:
  - Line items sum to subtotal
  - Subtotal + tax = total
  - All amounts are non-negative

**Why judges like this:**
- Deterministic math validation
- Clear financial semantics
- Works for OCR, LLM extraction, ERP exports

### 2. OCR → Structured Finance Parsing (`app/parsers/invoice_parser.py`)

Converts raw OCR JSON output into validated `Invoice` objects:

```python
from app.parsers.invoice_parser import parse_invoice_from_ocr

invoice = parse_invoice_from_ocr(ocr_json)
```

### 3. Validation & Reconciliation Engine (`app/validation/finance_validator.py`)

Deterministic validation with math + business rules:

```python
from app.validation.finance_validator import validate_invoice

result = validate_invoice(invoice)
# result.passed: bool
# result.errors: List[str]
# result.warnings: List[str]
```

**Enables:**
- Automatic rejection / human-review routing
- Validation pass-rate metrics
- Before/after fine-tune comparison

### 4. ETL Storage Model (`app/storage/finance_etl.py`)

Stores data at each stage of the ETL pipeline:

- `raw_ocr/` - Raw OCR output
- `parsed/` - Parsed Invoice objects
- `validated/` - Validation results
- `corrected/` - Human-corrected training gold data

```python
from app.storage.finance_etl import store_stage, load_stage, get_etl_pipeline

# Store at each stage
store_stage("raw_ocr", invoice_id, ocr_data)
store_stage("parsed", invoice_id, parsed_data)
store_stage("validated", invoice_id, validated_data)

# Retrieve complete pipeline
pipeline = get_etl_pipeline(invoice_id)
```

### 5. Active Learning Export (`app/training/active_learning.py`)

Export corrected invoices for fine-tuning:

```python
from app.training.active_learning import export_training_example

export_training_example(raw_ocr, corrected_invoice, invoice_id)
```

**Used when user clicks:** "Accept & Send to Training"

**This directly feeds:**
- PaddleOCR-VL fine-tuning
- LLaMA-Factory SFT
- Eval datasets

### 6. Finance Metrics (`app/metrics/finance_metrics.py`)

Metrics that judges care about:

```python
from app.metrics.finance_metrics import compute_invoice_metrics, compare_metrics

metrics = compute_invoice_metrics(invoices)
# Returns: total_docs, validation_pass_rate, avg_confidence, total_value, etc.

comparison = compare_metrics(before_metrics, after_metrics)
# Returns: pass_rate_improvement, confidence_improvement, error_rate_reduction
```

**This powers:**
- "Accuracy improved from X → Y"
- ROI justification
- One-slide results table

### 7. Complete Pipeline (`app/core/finance_processor.py`)

High-level processor that wires everything together:

```python
from app.core.finance_processor import FinanceProcessor

processor = FinanceProcessor()

# Process invoice through complete pipeline
result = processor.process_invoice(ocr_json, invoice_id="INV-001", export_for_training=True)

# Store human corrections
processor.correct_invoice(invoice_id, corrected_data)

# Get metrics
metrics = processor.get_metrics(invoices)

# Get complete pipeline data
pipeline = processor.get_pipeline_data(invoice_id)
```

## Usage Examples

See `examples/finance_data_layer_example.py` for complete examples:

1. **Simple Processing**: Process an invoice from OCR output
2. **Manual Validation**: Create and validate Invoice objects manually
3. **Metrics**: Compute aggregate metrics across multiple invoices
4. **Comparison**: Compare metrics before/after improvements

## Why This Wins Hackathons

You now demonstrate:

✅ **Real finance correctness** (math + rules)  
✅ **Auditable AI pipeline** (full ETL traceability)  
✅ **Human-in-the-loop learning** (active learning export)  
✅ **Reproducible ETL** (stage-by-stage storage)  
✅ **Business-grade structure** (Pydantic validation)

Most teams stop at OCR text. You ship finance-ready data.

## Next Steps

Potential enhancements:

1. **FastAPI Endpoint**: Full `/process_invoice` endpoint wiring all of this
2. **Streamlit/React UI**: Edit Invoice fields live
3. **Evaluation Notebook**: Baseline vs fine-tuned comparison
4. **CSV / QuickBooks Export**: Adapters for common formats
5. **Prefect/Airflow DAG**: Orchestration using this exact model

## File Structure

```
app/
├── models/
│   └── finance.py              # Pydantic models (Money, Vendor, LineItem, Invoice)
├── parsers/
│   └── invoice_parser.py      # OCR → Invoice parsing
├── validation/
│   └── finance_validator.py   # Validation engine
├── storage/
│   └── finance_etl.py         # ETL stage storage
├── training/
│   └── active_learning.py     # Training export
├── metrics/
│   └── finance_metrics.py     # Metrics computation
└── core/
    └── finance_processor.py   # Complete pipeline processor
```

## Testing

Run the example:

```bash
python examples/finance_data_layer_example.py
```

## Dependencies

All dependencies are already in `requirements.txt`:
- `pydantic>=2.5.0` (for models)
- Standard library (json, pathlib, datetime, decimal)

