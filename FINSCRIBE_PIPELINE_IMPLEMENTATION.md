# FinScribe Smart Scan - Complete Pipeline Implementation

This document describes the complete OCR + finance semantics pipeline implementation.

## 📁 Files Created/Updated

### 1. `finscribe/tasks.py` ✅
Complete Celery task pipeline:
- `ocr_task`: Performs OCR on images using PaddleOCR or Mock client
- `semantic_parse_task`: Parses OCR artifacts into structured finance JSON
- Uses `get_storage()` from staging module
- Uses `ocr_client` configured via `MODEL_MODE` env var
- Automatically enqueues semantic parsing after OCR

### 2. `paddle_server/app.py` ✅
Local PaddleOCR HTTP server (FREE, no cloud):
- FastAPI server on port 8002 (configurable)
- POST `/predict` endpoint accepts multipart/form-data images
- Returns JSON with regions array
- Runs locally with optional GPU support

### 3. `finscribe/db/models.py` ✅
SQLAlchemy models:
- `Job`: Simplified job tracking (id, status, created_at)
- `OCRResult`: Stores OCR data per job_id
- `ParsedResult`: Stores structured finance JSON per job_id

### 4. `alembic/versions/004_add_finscribe_pipeline_tables.py` ✅
Alembic migration:
- Creates `ocr_results` table
- Creates `parsed_results` table
- Foreign keys to existing `jobs` table

### 5. `ui/app.py` ✅
Streamlit UI:
- Simple file upload interface
- Uploads to `/api/v1/analyze`
- Polls `/api/v1/results/{job_id}` for results
- Displays structured JSON output

## 🚀 Setup Instructions

### 1. Install Dependencies

```bash
# Core dependencies
pip install celery redis sqlalchemy alembic

# PaddleOCR server
pip install paddlepaddle paddleocr fastapi uvicorn pillow

# Streamlit UI
pip install streamlit requests

# For storage (choose one):
# Local filesystem (default) - no extra install needed
# OR MinIO/S3
pip install boto3
```

### 2. Start PaddleOCR Server

```bash
# Option 1: CPU mode (default)
MODEL_MODE=paddle OCR_ENDPOINT=http://localhost:8002/predict \
uvicorn paddle_server.app:app --host 0.0.0.0 --port 8002

# Option 2: GPU mode (if CUDA available)
# Update paddle_server/app.py: use_gpu=True
```

### 3. Start Redis (for Celery)

```bash
# Using Docker
docker run -d -p 6379:6379 redis:alpine

# Or install locally
redis-server
```

### 4. Run Celery Worker

```bash
# Set environment
export MODEL_MODE=paddle  # or "mock" for testing
export OCR_ENDPOINT=http://localhost:8002/predict  # if using paddle mode
export CELERY_BROKER_URL=redis://localhost:6379/0

# Start worker
celery -A finscribe.celery_app worker --loglevel=info
```

### 5. Run Database Migrations

```bash
# Run Alembic migrations
alembic upgrade head
```

### 6. Start Streamlit UI

```bash
# Set API URL
export API_URL=http://localhost:8000

# Start UI
streamlit run ui/app.py
```

## 🔧 Configuration

### Environment Variables

```bash
# OCR Configuration
MODEL_MODE=paddle  # or "mock"
OCR_ENDPOINT=http://localhost:8002/predict  # PaddleOCR server URL
OCR_USE_GPU=false  # Set to true if CUDA available

# Storage
STORAGE_BASE=./storage  # Local filesystem base path
# OR for MinIO/S3:
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=finscribe

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Database
DATABASE_URL=postgresql://user:pass@localhost/finscribe
# OR for SQLite (dev):
DATABASE_URL=sqlite:///./finscribe.db

# Logging
LOGLEVEL=INFO
```

## 📊 Pipeline Flow

```
1. Upload document → API endpoint
2. API enqueues ocr_task(job_id, page_key, image_storage_key)
3. OCR task:
   - Reads image from storage
   - Calls ocr_client.analyze_image()
   - Saves OCR artifact to ocr/{job_id}/page_0.json
   - Enqueues semantic_parse_task(job_id, ocr_key)
4. Semantic parse task:
   - Reads OCR artifact
   - Calls parse_ocr_artifact_to_structured()
   - Saves structured JSON to results/{job_id}/structured.json
5. Result available via API
```

## 🎯 Features

✅ **FREE OCR**: PaddleOCR runs locally (no cloud API costs)  
✅ **Celery Pipeline**: Async task processing with Redis  
✅ **Storage Abstraction**: Local filesystem or MinIO/S3  
✅ **Semantic Parsing**: Invoice/receipt field extraction  
✅ **Database Persistence**: SQLAlchemy + Alembic migrations  
✅ **Live UI**: Streamlit interface for testing  
✅ **No Edge Functions**: All processing runs locally  

## 🔜 Next Steps

High-impact enhancements available:
- Invoice-specific regex + table heuristics
- PaddleOCR-VL fine-tuning hooks
- Batch PDF page splitting
- Confidence heatmaps + bbox overlays
- pytest fixtures for invoices

