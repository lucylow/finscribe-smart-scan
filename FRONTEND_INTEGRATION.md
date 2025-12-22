# FinScribe Smart Scan - Frontend Integration

## Overview

This document describes the hackathon-grade frontend integration for FinScribe Smart Scan that integrates:

1. **Unsloth** → Fast fine-tuned OCR/LLM reasoning
2. **CAMEL-AI** → Multi-agent verification & reasoning
3. **LLaMA** (via LLaMA-Factory or local inference) → Structured invoice understanding

## Architecture

```
Frontend (Streamlit / React)
        |
        v
/process_invoice  (FastAPI)
        |
        +--> PaddleOCR-VL (real OCR)
        |
        +--> Unsloth Fine-Tuned LLaMA (field extraction)
        |
        +--> CAMEL Agents
              - Extractor Agent
              - Validator Agent
              - Auditor Agent
        |
        +--> JSON + Validation + Confidence
```

**Key Design Principle**: Frontend does not talk directly to Unsloth/CAMEL/LLaMA — it talks to one unified API. This is critical for cleanliness and judge confidence.

## Components

### 1. Unified AI Gateway (`app/api/v1/process_invoice.py`)

The `/api/v1/process_invoice` endpoint provides a single API that:

- Receives invoice file upload
- Runs OCR (PaddleOCR-VL)
- Extracts structured JSON (Unsloth)
- Validates with CAMEL multi-agent system
- Returns unified response

**Response Format:**
```json
{
  "invoice_id": "uuid",
  "ocr_preview": "...raw text...",
  "structured_invoice": { ... },
  "camel_analysis": {
    "issues": [],
    "confidence": 0.97,
    "notes": "Totals validated, tax consistent"
  },
  "latency_ms": {
    "ocr": 480,
    "llm": 720,
    "agents": 310
  }
}
```

### 2. CAMEL Multi-Agent System (`app/agents/camel_invoice.py`)

Three specialized agents:

- **Extractor Agent**: Extracts invoice fields accurately
- **Validator Agent**: Validates financial correctness (totals, tax, arithmetic)
- **Auditor Agent**: Assesses confidence and lists risks/uncertainties

**Why judges care:**
- Multi-agent reasoning
- Explicit validation logic
- Not just "LLM magic"

### 3. Streamlit Frontend (`frontend/app.py`)

Features:
- **OCR Preview** - View raw OCR text
- **CAMEL Agent Verdict** - See confidence scores and validation notes
- **Editable Invoice** - Correct extracted data in real-time
- **Active Learning** - Send corrections to training queue
- **Performance Metrics** - See latency for each stage

### 4. Active Learning Endpoint (`app/api/v1/active_learning.py`)

Accepts corrected invoice data and saves to `data/active_learning.jsonl` for future fine-tuning.

## Quick Start

### Backend

```bash
# Start FastAPI backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
# Install dependencies
cd frontend
pip install -r requirements.txt

# Run Streamlit
streamlit run app.py
```

Or use the quick start script:
```bash
cd frontend
./run.sh
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY` - For CAMEL agents (optional, uses OpenAI if set)
- `VLLM_API_URL` or `LLAMA_API_URL` - For local LLaMA inference
- `UNSLOTH_MODEL_DIR` - Path to fine-tuned Unsloth model (default: `./models/unsloth-finscribe`)
- `PADDLEOCR_VLLM_URL` - OCR service URL (default: `http://localhost:8001/v1`)
- `ACTIVE_LEARNING_FILE` - Path to active learning JSONL file (default: `data/active_learning.jsonl`)

## Judge Talk Track (30 seconds)

> "FinScribe combines real OCR, a fine-tuned Unsloth LLaMA model, and CAMEL multi-agent validation. The frontend lets users correct invoices live, and those corrections feed active learning. We don't just extract text — we validate financial correctness and show confidence."

**This hits:**
- ✅ Technical depth
- ✅ Required model usage (Unsloth, CAMEL, LLaMA)
- ✅ Business credibility
- ✅ Active learning pipeline

## File Structure

```
finscribe-smart-scan/
├── app/
│   ├── api/v1/
│   │   ├── process_invoice.py      # Unified AI gateway
│   │   └── active_learning.py      # Active learning endpoint
│   ├── agents/
│   │   └── camel_invoice.py        # CAMEL multi-agent system
│   └── parsers/
│       └── json_parser.py          # Safe JSON parsing utility
├── frontend/
│   ├── app.py                      # Streamlit frontend
│   ├── requirements.txt
│   ├── README.md
│   └── run.sh                      # Quick start script
└── FRONTEND_INTEGRATION.md         # This file
```

## Next Steps (Optional Enhancements)

1. **Bounding-box overlay UI** - Visual wow factor
2. **Metric slide** - Baseline vs fine-tuned comparison
3. **docker-compose up demo** - One-command demo
4. **React version** - Instead of Streamlit

## Testing

### Test the API directly:

```bash
curl -X POST "http://localhost:8000/api/v1/process_invoice" \
  -F "file=@examples/sample_invoice_1.png"
```

### Test the frontend:

1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && streamlit run app.py`
3. Upload an invoice image
4. Review results and make corrections
5. Click "Accept & Send to Training"

## Troubleshooting

### Backend not starting
- Check if port 8000 is available
- Verify all dependencies are installed: `pip install -r requirements.txt`

### CAMEL agents not working
- Install CAMEL-AI: `pip install 'camel-ai[all]'`
- Check environment variables for model configuration

### Unsloth not available
- Model will fall back to mock mode if not loaded
- Set `UNSLOTH_MODEL_DIR` to point to your fine-tuned model

### OCR service not available
- Check `PADDLEOCR_VLLM_URL` environment variable
- OCR will use fallback text if service unavailable

