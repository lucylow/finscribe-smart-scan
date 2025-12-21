# FinScribe ETL Pipeline

Production-ready Extract-Transform-Load pipeline for financial document processing.

## Overview

This ETL pipeline provides a complete workflow for processing financial documents:

1. **Extract**: Ingest documents from multiple sources (local, S3/MinIO, bytes)
2. **Transform**: OCR, semantic parsing, normalization
3. **Load**: Store structured data in PostgreSQL and MinIO
4. **Validate**: Business rule validation

## Architecture

```
Raw Documents
    ↓
[Ingestion] → Local/S3/Bytes
    ↓
[Preprocessing] → Deskew, Contrast, Denoise
    ↓
[OCR] → PaddleOCR / HuggingFace / External
    ↓
[Semantic Parser] → VLM + Heuristic Fallback
    ↓
[Normalizer] → Dates, Currency, Text
    ↓
[Validator] → Arithmetic, Business Rules
    ↓
[Persistence] → PostgreSQL + MinIO
```

## Modules

### `ingestion.py`
Multi-source document ingestion:
- `ingest_from_local(path)` - Local filesystem
- `ingest_from_minio(bucket, object_key)` - MinIO/S3 buckets
- `ingest_from_bytes(bytes, filename)` - Raw bytes (API uploads)

### `preprocess.py`
Image preprocessing for OCR optimization:
- `deskew(image)` - Rotation correction
- `enhance_contrast(image)` - CLAHE contrast enhancement
- `denoise(image)` - Noise reduction
- `preprocess(path)` - Full preprocessing pipeline

### `ocr_client.py`
Multi-backend OCR abstraction:
- `run_ocr(path)` - Run OCR using configured backend
- Supports: `local`, `hf`, `paddleocr_direct`

### `semantic_parser.py`
Structured field extraction:
- `parse(ocr_json)` - Extract invoice fields
- Uses VLM endpoint with heuristic fallback
- Extracts: vendor, invoice_number, dates, line_items, totals

### `normalizer.py`
Data normalization:
- `normalize_date(s)` - ISO format (YYYY-MM-DD)
- `normalize_currency(s)` - Float conversion
- `normalize_invoice_data(data)` - Full invoice normalization

### `validator.py`
Business rule validation:
- `check_arithmetic(parsed)` - Subtotal + tax = total
- `check_required_fields(parsed)` - Required field presence
- `validate(parsed)` - Complete validation suite

### `persistence.py`
Structured data storage:
- `save_invoice(parsed, raw_ocr, source_path)` - PostgreSQL
- `save_to_minio(data, bucket, object_key)` - MinIO/S3

## Usage

### Basic Pipeline

```python
from data_pipeline.ingestion import ingest_from_local
from data_pipeline.preprocess import preprocess
from data_pipeline.ocr_client import run_ocr
from data_pipeline.semantic_parser import parse
from data_pipeline.normalizer import normalize_invoice_data
from data_pipeline.validator import validate
from data_pipeline.persistence import save_invoice

# Extract
src = ingest_from_local("invoice.png")
clean = preprocess(src)
ocr = run_ocr(clean)

# Transform
parsed = parse(ocr)
normalized = normalize_invoice_data(parsed)

# Validate
validation = validate(normalized)

# Load
invoice_id = save_invoice(normalized, ocr, src)
```

### Via FastAPI

```bash
# Upload file
curl -X POST "http://localhost:8000/api/v1/etl/ingest_upload" \
  -F "file=@invoice.png"

# Process local file
curl -X POST "http://localhost:8000/api/v1/etl/ingest_local?path=/path/to/invoice.png"
```

### Via Prefect

```python
from flows.invoice_etl_flow import invoice_etl_flow

result = invoice_etl_flow("invoice.png")
print(f"Invoice ID: {result['invoice_id']}")
```

### Via Airflow

See `dags/invoice_etl_dag.py` for complete DAG definition.

## Configuration

Set environment variables:

```bash
# OCR Backend
OCR_BACKEND=local  # or: hf, paddleocr_direct
OCR_LOCAL_ENDPOINT=http://localhost:8001/api/ocr
HF_OCR_ENDPOINT=https://api-inference.huggingface.co/ocr
HF_TOKEN=hf_xxx

# VLM Endpoint
VLM_ENDPOINT=http://vlm-service:8000/api/extract

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=finscribe
POSTGRES_USER=finscribe
POSTGRES_PASSWORD=password

# MinIO/S3
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_USE_SSL=false
```

## Database Schema

The pipeline creates two tables:

### `invoices`
- `id` (SERIAL PRIMARY KEY)
- `invoice_number` (TEXT)
- `vendor` (JSONB)
- `financial_summary` (JSONB)
- `raw_ocr` (JSONB)
- `source_path` (TEXT)
- `created_at` (TIMESTAMP)

### `line_items`
- `id` (SERIAL PRIMARY KEY)
- `invoice_id` (INT REFERENCES invoices)
- `description` (TEXT)
- `qty` (NUMERIC)
- `unit_price` (NUMERIC)
- `line_total` (NUMERIC)

Run migration:
```bash
alembic upgrade head
```

## Testing

```bash
pytest tests/test_etl_pipeline.py -v
```

## Notebook Demo

See `notebooks/01_finscribe_full_etl_demo.ipynb` for a complete Colab-friendly demo.

## Error Handling

All modules include comprehensive error handling:
- File not found → `FileNotFoundError`
- Unsupported format → `ValueError`
- OCR failure → `RuntimeError`
- Validation failure → Returns `{"ok": False, "errors": [...]}`

## Performance

- **Preprocessing**: ~100-500ms per image
- **OCR**: Depends on backend (1-10s)
- **Parsing**: VLM ~2-5s, Heuristic ~10-50ms
- **Validation**: <10ms
- **Persistence**: ~50-200ms

## Future Enhancements

- [ ] Streaming pipeline support
- [ ] Distributed processing (Celery)
- [ ] Advanced table extraction
- [ ] ML-based field extraction
- [ ] Active learning integration
- [ ] Real-time metrics dashboard

