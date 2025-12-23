# FinScribe Smart Scan Architecture

## Overview

FinScribe Smart Scan is an end-to-end invoice processing system that extracts structured data from invoice images using OCR, semantic parsing, and validation.

## Architecture Diagram

```
┌─────────────────┐
│  Invoice Image  │
│  (PNG/JPG/PDF)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   FastAPI Backend               │
│   POST /process_invoice         │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Preprocessing                  │
│   - Deskew                      │
│   - CLAHE enhancement           │
│   - Denoise                     │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   OCR (PaddleOCR)               │
│   Modes:                        │
│   - service (HTTP)              │
│   - local (library)             │
│   - mock (demo)                 │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Semantic Parser               │
│   - Extract vendor info         │
│   - Parse line items table       │
│   - Extract financial summary   │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Validation                    │
│   - ERNIE LLM (if available)    │
│   - Basic arithmetic checks      │
│   - Fallback mode               │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Response                      │
│   - Structured JSON             │
│   - Validation results           │
│   - Confidence scores            │
└─────────────────────────────────┘
```

## Component Details

### Backend API (`backend/main.py`)
- FastAPI application
- Endpoints:
  - `POST /process_invoice` - Process invoice file
  - `POST /active_learning` - Accept corrections
  - `GET /health` - Health check

### OCR Client (`backend/ocr/paddle_client.py`)
- Supports three modes:
  - **service**: HTTP POST to OCR service
  - **local**: Direct PaddleOCR library call
  - **mock**: Deterministic sample data for demos

### Pipeline (`backend/pipeline/invoice_pipeline.py`)
- Orchestrates full processing flow
- Stages:
  1. Preprocess image
  2. Run OCR
  3. Parse regions (vendor, line items, totals)
  4. Validate with ERNIE or basic validator
  5. Store intermediate results

### Validation (`backend/llm/ernie_client.py`)
- ERNIE LLM validation (if `ERNIE_URL` set)
- Mock fallback for local demos
- Arithmetic checks (subtotal, tax, total)

### Storage (`backend/storage/etl.py`)
- Stores pipeline stages to `data/<stage>/<invoice_id>.json`
- Active learning queue: `data/active_learning_queue.jsonl`

## Data Flow

1. **Upload**: User uploads invoice image via Streamlit UI or API
2. **Preprocess**: Image is deskewed and enhanced
3. **OCR**: Text and bounding boxes extracted
4. **Parse**: Structured data extracted (vendor, line items, totals)
5. **Validate**: Arithmetic and business logic validation
6. **Store**: Results stored in `data/` directory
7. **Return**: JSON response with structured invoice and validation

## Environment Variables

- `PADDLE_MODE`: `service` | `local` | `mock` (default: `mock`)
- `PADDLE_SERVICE_URL`: OCR service endpoint (default: `http://ocr-service:8001/predict`)
- `ERNIE_URL`: ERNIE validation service URL (optional)

## Deployment

### Local Development
```bash
make dev  # Starts docker-compose demo stack
```

### Docker Compose
- `backend`: FastAPI service (port 8000)
- `frontend`: Streamlit UI (port 8501)
- `ocr-service`: Mock OCR service (port 8001)

## Active Learning

When users correct invoice data in the UI and click "Accept & Send to Training":
1. Corrected JSON appended to `data/active_learning_queue.jsonl`
2. Can be used for fine-tuning models
3. Format: JSONL with invoice, corrections, metadata

## Testing

- Unit tests: `pytest tests/`
- Mock mode: All tests run without GPU/LLM dependencies
- CI: Runs tests and linting on push/PR

