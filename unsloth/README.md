# Unsloth Integration for FinScribe Smart Scan

Complete integration of Unsloth for efficient LLM fine-tuning and inference in the FinScribe Smart Scan application.

## Overview

Unsloth is an LLM training and inference framework that provides:
- **2× faster training** compared to baseline methods
- **70% less VRAM usage** with 4-bit quantization
- **Efficient inference** with FastLanguageModel

This integration enables fine-tuning LLMs for structured invoice extraction from OCR text, with active learning support for continuous improvement.

## Installation

### Option 1: Direct Installation

```bash
# Install Unsloth (adjust cu118 to match your CUDA version)
pip install --upgrade torch trl transformers datasets
pip install "unsloth[cu118] @ git+https://github.com/unslothai/unsloth.git"

# Or for CPU-only:
pip install "unsloth @ git+https://github.com/unslothai/unsloth.git"
```

### Option 2: Docker

```bash
# Build the LLM training container
docker-compose build llm

# Or build manually
docker build -f Dockerfile.llm -t finscribe-llm .
```

## Quick Start

### 1. Prepare Training Data

Convert your invoice data to Unsloth format:

```bash
python unsloth/prepare_training_data.py \
    --input data/active_learning.jsonl data/training_queue.jsonl \
    --output data/unsloth_train.jsonl \
    --val_output data/unsloth_val.jsonl \
    --split \
    --val_ratio 0.1
```

**Data Format**: Each line in the JSONL file should be:
```json
{
  "input": "OCR_TEXT:\nVendor: TechCorp Inc.\nInvoice #: INV-2024-001\n...",
  "output": "{\"vendor\": {\"name\": \"TechCorp Inc.\"}, \"invoice_number\": \"INV-2024-001\", ...}"
}
```

### 2. Fine-tune Model

```bash
python unsloth/train_unsloth_fast.py \
    --model_name unsloth/llama-3.1-8b-unsloth-bnb-4bit \
    --train_data data/unsloth_train.jsonl \
    --val_data data/unsloth_val.jsonl \
    --output_dir models/unsloth-finscribe \
    --num_epochs 3 \
    --batch_size 4 \
    --learning_rate 2e-5 \
    --lora_r 16 \
    --lora_alpha 32 \
    --load_in_4bit
```

**Using Docker:**
```bash
docker-compose run --rm llm python3 unsloth/train_unsloth_fast.py \
    --train_data data/unsloth_train.jsonl \
    --val_data data/unsloth_val.jsonl \
    --output_dir models/unsloth-finscribe
```

### 3. Use in Inference

The fine-tuned model is automatically loaded by the `UnslothService`:

```python
from app.core.models.unsloth_service import get_unsloth_service

service = get_unsloth_service()
result = service.infer(ocr_text="Vendor: TechCorp Inc.\nInvoice: INV-001...")
```

Or via API:
```bash
curl -X POST http://localhost:8000/api/v1/unsloth/infer \
    -H "Content-Type: application/json" \
    -d '{
        "ocr_text": "Vendor: TechCorp Inc.\nInvoice: INV-001...",
        "doc_id": "doc-123"
    }'
```

### 4. Evaluate Model

Compare baseline vs fine-tuned model:

```bash
python unsloth/evaluate_unsloth.py \
    --baseline_model unsloth/llama-3.1-8b-unsloth-bnb-4bit \
    --fine_tuned_model models/unsloth-finscribe \
    --test_data data/unsloth_val.jsonl \
    --output evaluation/unsloth_evaluation.json
```

## Active Learning Integration

When users correct invoice extractions in the UI, the corrections are automatically exported to Unsloth training format:

```python
from app.training.active_learning import export_training_example

# Export correction for fine-tuning
export_training_example(
    raw_ocr=ocr_result,
    corrected_invoice=corrected_json,
    invoice_id="inv-123"
)
```

This exports to both:
- `data/training_queue.jsonl` (general format)
- `data/unsloth_training_queue.jsonl` (Unsloth-specific format)

## Architecture

### Components

1. **UnslothService** (`app/core/models/unsloth_service.py`)
   - Loads models using FastLanguageModel
   - Handles inference with 4-bit quantization
   - Falls back to standard transformers if Unsloth unavailable

2. **Training Script** (`unsloth/train_unsloth_fast.py`)
   - Uses FastLanguageModel for efficient training
   - Supports LoRA/QLoRA fine-tuning
   - Configurable hyperparameters

3. **Data Preparation** (`unsloth/prepare_training_data.py`)
   - Converts various formats to Unsloth training format
   - Merges multiple datasets
   - Splits train/val sets

4. **Evaluation** (`unsloth/evaluate_unsloth.py`)
   - Compares baseline vs fine-tuned models
   - Field-level accuracy metrics
   - Detailed evaluation reports

### Pipeline Flow

```
OCR Text → UnslothService.infer() → Structured JSON
                ↓
         User Corrections
                ↓
    Active Learning Export
                ↓
    Training Data Preparation
                ↓
        Fine-tuning Script
                ↓
    Updated Model → Improved Inference
```

## Configuration

### Environment Variables

- `UNSLOTH_MODEL_DIR`: Path to fine-tuned model (default: `./models/unsloth-finscribe`)
- `UNSLOTH_MODEL_NAME`: Pre-trained model name (default: `unsloth/llama-3.1-8b-unsloth-bnb-4bit`)
- `HF_TOKEN`: HuggingFace token for private models

### Training Hyperparameters

Recommended settings for invoice extraction:

- **LoRA rank (r)**: 16-32 (higher = more parameters, better quality)
- **LoRA alpha**: 32-64 (typically 2x rank)
- **Learning rate**: 2e-5 to 5e-5
- **Batch size**: 2-4 (adjust based on VRAM)
- **Epochs**: 3-5
- **Max sequence length**: 2048 (sufficient for most invoices)

## Docker Setup

The `Dockerfile.llm` provides a complete training environment:

```bash
# Build
docker build -f Dockerfile.llm -t finscribe-llm .

# Run training
docker run --gpus all -v $(pwd):/app finscribe-llm \
    python3 unsloth/train_unsloth_fast.py \
    --train_data data/unsloth_train.jsonl
```

Or use docker-compose:
```bash
docker-compose run --rm llm python3 unsloth/train_unsloth_fast.py \
    --train_data data/unsloth_train.jsonl
```

## Troubleshooting

### CUDA Version Mismatch

If you get CUDA errors, check your CUDA version:
```bash
nvidia-smi
```

Then install the matching Unsloth version:
- CUDA 11.8: `unsloth[cu118]`
- CUDA 12.1: `unsloth[cu121]`
- CPU: `unsloth` (no CUDA suffix)

### Out of Memory

Reduce batch size or enable gradient checkpointing:
```bash
python unsloth/train_unsloth_fast.py \
    --batch_size 1 \
    --gradient_accumulation_steps 8
```

### Model Not Loading

Check that the model directory exists and contains:
- `config.json`
- `tokenizer.json` or `tokenizer_config.json`
- Model weights (`.safetensors` or `.bin` files)

## Performance Benchmarks

Expected improvements with Unsloth fine-tuning:

- **Training speed**: 2× faster than baseline
- **VRAM usage**: 70% reduction with 4-bit quantization
- **Extraction accuracy**: 10-30% improvement over baseline (depends on dataset size)

## Next Steps

1. **Collect more training data**: Use active learning to gather corrections
2. **Experiment with hyperparameters**: Try different LoRA ranks and learning rates
3. **Evaluate regularly**: Run evaluation script after each training run
4. **Deploy updated models**: Replace model in `UNSLOTH_MODEL_DIR` to use new fine-tuned model

## References

- [Unsloth GitHub](https://github.com/unslothai/unsloth)
- [Unsloth Documentation](https://github.com/unslothai/unsloth#readme)
- [HuggingFace Unsloth Models](https://huggingface.co/unsloth)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Unsloth GitHub issues
3. Check FinScribe documentation in `docs/`
