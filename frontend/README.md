# FinScribe Smart Scan - Streamlit Frontend

Hackathon-grade frontend integration for FinScribe Smart Scan that demonstrates:

- **Unsloth** → Fast fine-tuned OCR/LLM reasoning
- **CAMEL-AI** → Multi-agent verification & reasoning  
- **LLaMA** (via LLaMA-Factory or local inference) → Structured invoice understanding

## Quick Start

### 1. Start the Backend API

```bash
# From project root
cd /path/to/finscribe-smart-scan
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or use Docker:
```bash
docker-compose up backend
```

### 2. Start the Streamlit Frontend

```bash
# From frontend directory
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

The frontend will be available at `http://localhost:8501`

## Architecture

```
Frontend (Streamlit)
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

## Features

### Unified AI Gateway

The `/api/v1/process_invoice` endpoint provides a single API that:

1. **OCR Processing** - Extracts text from invoice images/PDFs
2. **LLM Extraction** - Uses Unsloth fine-tuned model to extract structured JSON
3. **Multi-Agent Validation** - CAMEL agents validate financial correctness
4. **Returns Unified Response** - Single response with all results

### Frontend Features

- **OCR Preview** - View raw OCR text
- **CAMEL Agent Verdict** - See confidence scores and validation notes
- **Editable Invoice** - Correct extracted data in real-time
- **Active Learning** - Send corrections to training queue
- **Performance Metrics** - See latency for each stage

## API Response Format

```json
{
  "invoice_id": "uuid",
  "ocr_preview": "...raw text...",
  "structured_invoice": {
    "vendor": {...},
    "invoice_number": "...",
    "line_items": [...],
    "financial_summary": {...}
  },
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

## Active Learning

When users correct invoice data and click "Accept & Send to Training", corrections are saved to `data/active_learning.jsonl` for future fine-tuning.

## Configuration

### Environment Variables

- `OPENAI_API_KEY` - For CAMEL agents (optional, uses OpenAI if set)
- `VLLM_API_URL` or `LLAMA_API_URL` - For local LLaMA inference
- `UNSLOTH_MODEL_DIR` - Path to fine-tuned Unsloth model
- `PADDLEOCR_VLLM_URL` - OCR service URL
- `ACTIVE_LEARNING_FILE` - Path to active learning JSONL file

## Judge Talk Track (30 seconds)

> "FinScribe combines real OCR, a fine-tuned Unsloth LLaMA model, and CAMEL multi-agent validation. The frontend lets users correct invoices live, and those corrections feed active learning. We don't just extract text — we validate financial correctness and show confidence."

This demonstrates:
- ✅ Technical depth
- ✅ Required model usage (Unsloth, CAMEL, LLaMA)
- ✅ Business credibility
- ✅ Active learning pipeline

