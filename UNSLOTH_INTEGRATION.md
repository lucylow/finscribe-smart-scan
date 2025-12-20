# Unsloth Integration Guide

This document provides a comprehensive guide to using Unsloth in your FinScribe project.

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Training](#training)
4. [Inference](#inference)
5. [Active Learning](#active-learning)
6. [Docker Deployment](#docker-deployment)
7. [Integration Examples](#integration-examples)

## Overview

Unsloth is integrated into FinScribe as the **reasoning/finalizer stage** that converts OCR text into structured JSON. The pipeline:

```
Document Image → PaddleOCR-VL → OCR Text → Unsloth → Structured JSON → Validation
```

### Key Components

- **`app/core/models/unsloth_service.py`**: Core inference service
- **`app/api/v1/unsloth.py`**: FastAPI endpoints
- **`unsloth/train_unsloth.py`**: Training script
- **`scripts/train_unsloth.sh`**: Training automation
- **`streamlit_unsloth/app.py`**: Active learning UI
- **`unsloth_api/`**: Standalone microservice
- **`ocr_service/`**: Standalone OCR service

## Installation

### Option 1: Integrated into Main Backend

The Unsloth service is already integrated. Just install dependencies:

```bash
# Install Unsloth (GPU required for training/inference)
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"

# Or for specific CUDA version:
# pip install "unsloth[cu124-torch250] @ git+https://github.com/unslothai/unsloth.git"
```

### Option 2: Standalone Services

Use Docker Compose profiles:

```bash
# Start Unsloth API service
docker-compose --profile unsloth up unsloth_api

# Start OCR service
docker-compose --profile ocr up ocr_service

# Start both
docker-compose --profile unsloth --profile ocr up
```

## Training

### Quick Start

```bash
# 1. Ensure you have demo datasets
ls data/unsloth_train.jsonl data/unsloth_val.jsonl

# 2. Run training script
./scripts/train_unsloth.sh
```

### Custom Training

```bash
# Set environment variables
export MODEL_NAME="unsloth/Mistral-7B-Instruct-v0.2-bnb-4bit"
export TRAIN_JSONL="./data/my_train.jsonl"
export VAL_JSONL="./data/my_val.jsonl"
export OUTPUT_DIR="./models/my-unsloth-model"
export NUM_EPOCHS=5
export BATCH_SIZE=2
export USE_LORA=true
export USE_QLORA=false

# Run training
python unsloth/train_unsloth.py
```

### Dataset Format

Training data should be in JSONL format:

```json
{"prompt": "OCR_TEXT:\nVendor: TechCorp...", "completion": "{\"document_type\":\"invoice\",...}"}
```

Each line is a JSON object with:
- `prompt`: Input OCR text with instruction
- `completion`: Target JSON output (as string)

## Inference

### Using FastAPI Endpoint

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/unsloth/infer",
    json={
        "ocr_text": "Vendor: TechCorp Inc.\nInvoice: INV-2024-001...",
        "doc_id": "doc-123"
    }
)

result = response.json()
print(result["parsed"])
```

### Using Python Service

```python
from app.core.models.unsloth_service import get_unsloth_service

service = get_unsloth_service()
result = service.infer(
    ocr_text="Vendor: TechCorp Inc.\nInvoice: INV-2024-001..."
)

print(result)
```

### Integrated into Document Processor

The Unsloth service can be integrated into your existing document processor:

```python
from app.core.models.unsloth_service import get_unsloth_service
from app.core.document_processor import FinancialDocumentProcessor

# In your processor
unsloth_service = get_unsloth_service()
ocr_text = extract_text_from_ocr(ocr_results)
structured_json = unsloth_service.infer(ocr_text)
```

## Active Learning

### Using Streamlit UI

1. Start the UI:
```bash
streamlit run streamlit_unsloth/app.py
```

2. Workflow:
   - Upload document → Run OCR → Send to Unsloth
   - Review parsed JSON
   - Correct any errors
   - Save correction to `data/active_learning.jsonl`

3. Retrain:
```bash
# Merge active learning data into training set
cat data/active_learning.jsonl >> data/unsloth_train.jsonl

# Retrain model
./scripts/train_unsloth.sh
```

## Docker Deployment

### Full Stack (OCR + Unsloth + Backend)

```yaml
# docker-compose.yml already includes:
services:
  backend:          # Main FinScribe API (includes Unsloth endpoints)
  unsloth_api:      # Standalone Unsloth service (GPU)
  ocr_service:      # Standalone OCR service
  postgres:         # Database
  minio:            # Object storage
```

Start specific services:
```bash
# Main backend (includes integrated Unsloth)
docker-compose up backend

# Or standalone services
docker-compose --profile unsloth --profile ocr up
```

### GPU Requirements

Unsloth requires GPU for inference. Ensure Docker has GPU access:

```bash
# Install nvidia-container-toolkit
# Then use runtime: nvidia in docker-compose.yml
```

## Integration Examples

### Example 1: Simple Inference

```python
from app.core.models.unsloth_service import UnslothService

# Initialize service
service = UnslothService(
    model_dir="./models/unsloth-finscribe",
    device="cuda"
)

# Run inference
ocr_text = """
Vendor: TechCorp Inc.
Invoice: INV-2024-001
Date: 2024-01-15
Item: Widget A Qty 2 Unit $50.00 Total $100.00
Subtotal: $100.00
Tax: $10.00
Total: $110.00
"""

result = service.infer(ocr_text)
print(json.dumps(result, indent=2))
```

### Example 2: Custom Instruction

```python
service = get_unsloth_service()

result = service.infer(
    ocr_text=ocr_text,
    instruction="\n\nExtract only vendor name and total amount as JSON.",
    max_new_tokens=256,
    temperature=0.0
)
```

### Example 3: Batch Processing

```python
def process_batch(ocr_texts):
    service = get_unsloth_service()
    results = []
    
    for ocr_text in ocr_texts:
        result = service.infer(ocr_text)
        results.append(result)
    
    return results
```

## Configuration

### Environment Variables

- `UNSLOTH_MODEL_DIR`: Path to fine-tuned model (default: `./models/unsloth-finscribe`)
- `MODEL_NAME`: Base model for training
- `TRAIN_JSONL`: Training dataset path
- `VAL_JSONL`: Validation dataset path
- `OUTPUT_DIR`: Model output directory
- `NUM_EPOCHS`: Training epochs
- `BATCH_SIZE`: Training batch size
- `USE_LORA`: Enable LoRA fine-tuning
- `USE_QLORA`: Enable QLoRA 4-bit quantization

### Model Configuration

Edit `unsloth/train_unsloth.py` to adjust:
- LoRA rank (`lora_r`)
- LoRA alpha (`lora_alpha`)
- Learning rate
- Sequence length
- Other hyperparameters

## Troubleshooting

### Common Issues

1. **Model not loading**
   - Check `MODEL_DIR` environment variable
   - Verify model files exist
   - Check GPU availability

2. **Out of memory**
   - Use QLoRA: Set `USE_QLORA=true`
   - Reduce batch size
   - Increase gradient accumulation

3. **Poor JSON extraction**
   - Improve training data quality
   - Add more diverse examples
   - Fine-tune instruction prompts

4. **Slow inference**
   - Use GPU (CUDA)
   - Enable model quantization
   - Reduce `max_new_tokens`

## Next Steps

1. **Collect Real Data**: Replace synthetic datasets with real invoice data
2. **Fine-tune Prompts**: Optimize instruction prompts for your use case
3. **Scale Training**: Use larger datasets (100+ examples) for better results
4. **Active Learning**: Continuously improve model with corrections
5. **Evaluation**: Set up evaluation metrics to track model performance

## Resources

- [Unsloth GitHub](https://github.com/unslothai/unsloth)
- [Unsloth Docs](https://docs.unsloth.ai/)
- [Unsloth Hugging Face](https://huggingface.co/unsloth)
- [Training Guide](unsloth/README.md)
- [Demo Datasets](data/README.md)

