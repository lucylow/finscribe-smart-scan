# OCR Pipeline Setup Guide

This document describes the new local PaddleOCR-based OCR pipeline implementation.

## Overview

The OCR pipeline uses:
- **PaddleOCR** for local OCR processing (no cloud/edge functions)
- **Celery** for background task processing
- **Staging** for PDF/image preprocessing
- **MinIO/LocalStorage** for artifact storage

## Architecture

```
Upload → API Endpoint → Staging → Celery Queue → OCR Task → Storage
```

1. **Upload**: `POST /api/v1/analyze-ocr` accepts PDF/image files
2. **Staging**: Converts PDFs to per-page PNGs, normalizes images
3. **Queue**: Enqueues OCR task per page to Celery
4. **Processing**: Worker processes pages with PaddleOCR
5. **Storage**: Saves OCR JSON artifacts to MinIO/local storage

## Setup

### 1. Install Dependencies

#### CPU Installation (Recommended for development)
```bash
# Install PaddlePaddle CPU version
pip install paddlepaddle==2.5.0 -f https://www.paddlepaddle.org.cn/whl/linux/mkl/avx/stable.html

# Install PaddleOCR
pip install paddleocr==2.6.1.0

# Install other dependencies
pip install -r requirements.txt
```

#### GPU Installation (For production with GPU)
```bash
# Install PaddlePaddle GPU version (adjust CUDA version as needed)
pip install paddlepaddle-gpu==2.5.0

# Install PaddleOCR
pip install paddleocr==2.6.1.0
```

### 2. Environment Variables

```bash
# OCR Configuration
OCR_MODE=paddle          # or "mock" for testing
OCR_LANG=en              # Language code
OCR_USE_GPU=0            # Set to 1 for GPU

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Storage Configuration
STORAGE_BASE=./storage    # For LocalStorage
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
STORAGE_BUCKET=finscribe
```

### 3. Start Services

#### Using Docker Compose (Recommended)
```bash
# Start all services including worker
docker-compose up --build

# Or start specific services
docker-compose up api redis postgres minio worker
```

#### Manual Setup
```bash
# Start Redis
redis-server

# Start Celery worker
export CELERY_BROKER_URL=redis://localhost:6379/0
export OCR_MODE=mock  # or "paddle"
celery -A finscribe.celery_app.celery_app worker --loglevel=info -Q ocr

# Start API server
uvicorn app.main:app --reload
```

## Usage

### API Endpoint

```bash
# Upload a document
curl -X POST http://localhost:8000/api/v1/analyze-ocr \
  -F "file=@examples/sample_invoice_1.png"

# Response:
# {
#   "job_id": "550e8400-e29b-41d4-a716-446655440000",
#   "poll_url": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000",
#   "status": "queued",
#   "message": "Job received and queued. Processing 1 page(s)."
# }

# Poll for status
curl http://localhost:8000/api/v1/jobs/{job_id}
```

### Python Usage

```python
from finscribe.ocr_client import get_ocr_client
from finscribe.staging import LocalStorage, stage_upload

# Get OCR client
client = get_ocr_client()  # Uses OCR_MODE env var

# Stage a file
storage = LocalStorage("./storage")
with open("invoice.pdf", "rb") as f:
    file_bytes = f.read()
page_keys = stage_upload(file_bytes, "invoice.pdf", "job_123", storage)

# Run OCR on a page
image_bytes = storage.get_bytes(page_keys[0])
regions = client.analyze_image_bytes(image_bytes)
print(regions)
```

## Testing

### Unit Tests
```bash
# Run OCR client tests
pytest tests/test_ocr_client.py

# Run staging tests
pytest tests/test_staging.py

# Run task tests
pytest tests/test_ocr_tasks.py
```

### Smoke Test
```bash
# Run smoke test (requires docker-compose to be running)
./scripts/smoke_test.sh

# Or with custom file
TEST_FILE=examples/sample_invoice_2.png ./scripts/smoke_test.sh
```

## File Structure

```
finscribe/
├── ocr_client.py      # OCR client abstraction (PaddleOCR, Mock)
├── staging.py         # PDF/image staging utilities
├── celery_app.py     # Celery app configuration
└── tasks.py          # OCR Celery tasks

app/api/v1/
└── ocr_endpoints.py  # API endpoint for OCR pipeline

tests/
├── test_ocr_client.py
├── test_staging.py
└── test_ocr_tasks.py

scripts/
└── smoke_test.sh    # End-to-end smoke test
```

## Storage Artifacts

The pipeline stores artifacts with the following structure:

```
raw/{job_id}/original.pdf          # Original uploaded file
staging/{job_id}/page_{i}.png     # Staged page images
ocr/{job_id}/page_{i}.png.json    # OCR results per page
```

## Troubleshooting

### PaddleOCR Import Error
```bash
# Make sure PaddlePaddle is installed first
pip install paddlepaddle==2.5.0
pip install paddleocr==2.6.1.0
```

### Worker Not Processing Tasks
```bash
# Check worker logs
docker-compose logs worker

# Check Redis connection
redis-cli ping

# Verify Celery is connected
celery -A finscribe.celery_app.celery_app inspect active
```

### Storage Issues
```bash
# For LocalStorage, ensure directory exists
mkdir -p ./storage

# For MinIO, check connection
curl http://localhost:9000/minio/health/live
```

## Performance Notes

- **CPU Mode**: Slower but works on any machine (~2-5s per page)
- **GPU Mode**: Much faster (~0.5-1s per page) but requires CUDA
- **Mock Mode**: Instant, for testing only

## Next Steps

1. Integrate semantic parser to process OCR results
2. Add result aggregation for multi-page documents
3. Implement job status tracking in database
4. Add metrics and monitoring

