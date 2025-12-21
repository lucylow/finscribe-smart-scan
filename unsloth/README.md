# Unsloth Integration for FinScribe

This directory contains the Unsloth integration for FinScribe, providing fine-tuning and inference capabilities for structured JSON extraction from OCR text.

## Overview

Unsloth acts as the **reasoning/finalizer stage** in the FinScribe pipeline:
1. **OCR Stage**: PaddleOCR-VL extracts text and layout from documents
2. **Unsloth Stage**: Fine-tuned LLM converts OCR text → structured JSON
3. **Validation Stage**: Financial validator checks extracted data

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv_unsloth
source venv_unsloth/bin/activate

# Install Unsloth (choose CUDA variant for your system)
pip install --upgrade "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install --upgrade "unsloth-zoo @ git+https://github.com/unslothai/unsloth_zoo.git"

# Install other dependencies
pip install -r unsloth/requirements.txt
```

**CUDA Variants:**
- `unsloth[colab-new]` - Colab/newer systems
- `unsloth[cu124-torch250]` - CUDA 12.4 + PyTorch 2.5.0
- `unsloth[cu121-torch250]` - CUDA 12.1 + PyTorch 2.5.0
- `unsloth[cu118-torch250]` - CUDA 11.8 + PyTorch 2.5.0

### 2. Prepare Dataset

Demo datasets are provided in `data/`:
- `data/unsloth_train.jsonl` - Training examples (10 samples)
- `data/unsloth_val.jsonl` - Validation examples (2 samples)
- `data/active_learning_seed.jsonl` - Seed for human corrections

Format:
```json
{"prompt": "OCR_TEXT:\nVendor: TechCorp...", "completion": "{\"document_type\":\"invoice\",...}"}
```

### 3. Train Model

```bash
# Using the training script
./scripts/train_unsloth.sh

# Or manually:
python unsloth/train_unsloth.py
```

**Environment Variables:**
- `MODEL_NAME` - Base model (default: `unsloth/Mistral-7B-Instruct-v0.2-bnb-4bit`)
- `TRAIN_JSONL` - Training file path
- `VAL_JSONL` - Validation file path
- `OUTPUT_DIR` - Output directory (default: `./models/unsloth-finscribe`)
- `NUM_EPOCHS` - Number of training epochs (default: 3)
- `BATCH_SIZE` - Batch size (default: 1)
- `USE_LORA` - Use LoRA fine-tuning (default: true)
- `USE_QLORA` - Use QLoRA 4-bit quantization (default: false)

### 4. Use Inference API

**Option A: Integrated into Main Backend**

The Unsloth service is integrated into the main FastAPI backend:
```bash
# Start backend (includes Unsloth endpoints)
docker-compose up backend

# Call Unsloth endpoint
curl -X POST http://localhost:8000/api/v1/unsloth/infer \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_text": "Vendor: TechCorp Inc.\nInvoice: INV-2024-001...",
    "doc_id": "doc-123"
  }'
```

**Option B: Standalone Service**

Run Unsloth as a separate microservice:
```bash
# Start standalone service
docker-compose --profile unsloth up unsloth_api

# Or manually:
cd unsloth_api
uvicorn app.unsloth_api:app --host 0.0.0.0 --port 8001
```

### 5. Streamlit UI for Active Learning

```bash
# Install Streamlit dependencies
pip install streamlit requests

# Run UI
streamlit run streamlit_unsloth/app.py
```

The UI allows you to:
1. Upload documents
2. Run OCR
3. Send to Unsloth for JSON extraction
4. Correct parsed outputs
5. Save corrections for retraining

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  PaddleOCR  │ ──> │   Unsloth    │ ──> │   JSON      │
│     -VL     │     │  (Fine-tuned)│     │  Output     │
└─────────────┘     └──────────────┘     └─────────────┘
     OCR Text          Structured          Validated
                      JSON Extract          Data
```

## Training Tips

1. **LoRA vs QLoRA vs Full Fine-tune:**
   - **LoRA** (recommended): Fast, memory-efficient, good for most use cases
   - **QLoRA**: Even more memory-efficient (4-bit), use for large models on limited GPU
   - **Full Fine-tune**: Best quality but requires more GPU memory

2. **Data Quality:**
   - Create diverse training examples covering edge cases
   - Ensure JSON format consistency
   - Include examples with errors to teach correction

3. **Hyperparameters:**
   - Start with default LoRA settings (r=16, alpha=32)
   - Adjust learning rate (2e-5 is a good starting point)
   - Use gradient accumulation to simulate larger batch sizes

4. **Active Learning Loop:**
   - Collect corrections via Streamlit UI
   - Merge into training dataset
   - Retrain periodically to improve model

## API Reference

### POST `/api/v1/unsloth/infer`

**Request:**
```json
{
  "ocr_text": "Vendor: TechCorp Inc.\nInvoice: INV-2024-001...",
  "doc_id": "optional-doc-id",
  "instruction": "optional custom instruction",
  "max_new_tokens": 512,
  "temperature": 0.0
}
```

**Response:**
```json
{
  "doc_id": "optional-doc-id",
  "parsed": {
    "document_type": "invoice",
    "vendor": {"name": "TechCorp Inc."},
    "line_items": [...],
    "financial_summary": {...}
  },
  "model_available": true
}
```

### GET `/api/v1/unsloth/health`

Check if Unsloth model is loaded and available.

## Docker Setup

### Unsloth API Service

```yaml
# docker-compose.yml
services:
  unsloth_api:
    build: ./unsloth_api
    runtime: nvidia  # Requires GPU
    environment:
      - MODEL_DIR=/models/unsloth-finscribe
    volumes:
      - ./models:/models
    ports:
      - "8001:8000"
```

### OCR Service

```yaml
services:
  ocr_service:
    build: ./ocr_service
    ports:
      - "8002:8000"
```

## Colab Training

For training in Google Colab, see the notebook format in `UNSLOTH_COLAB_NOTEBOOK.ipynb` or copy the Python code from `train_unsloth.py` into Colab cells.

**Quick Colab Setup:**
1. Runtime → Change runtime type → GPU (T4 or better)
2. Install dependencies (Cell 1)
3. Generate dataset (Cell 2)
4. Load model with Unsloth (Cell 3)
5. Train (Cell 4)
6. Test inference (Cell 5)

## Troubleshooting

### Model Not Loading
- Check `MODEL_DIR` environment variable
- Ensure model files exist in the directory
- Check GPU availability: `torch.cuda.is_available()`

### Out of Memory
- Use QLoRA (4-bit quantization): Set `USE_QLORA=true`
- Reduce batch size: Set `BATCH_SIZE=1`
- Increase gradient accumulation: Set `GRADIENT_ACCUMULATION_STEPS=16`

### Training Errors
- Verify dataset format (JSONL with "prompt" and "completion" keys)
- Check tokenizer compatibility with model
- Ensure sufficient disk space for model checkpoints

## References

- [Unsloth GitHub](https://github.com/unslothai/unsloth)
- [Unsloth Docs](https://docs.unsloth.ai/)
- [Unsloth Hugging Face](https://huggingface.co/unsloth)

## License

Check model licenses before commercial use. Unsloth models use various licenses - see Hugging Face model cards.


