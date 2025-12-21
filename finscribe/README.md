# FinScribe PaddleOCR-VL Fine-Tuning System

Complete implementation for fine-tuning PaddleOCR-VL-0.9B for financial document intelligence.

## Overview

This system provides:
- **Dataset preparation** with instruction-style formatting
- **Completion-only training** with proper loss masking
- **Hard-sample mining** for iterative improvement
- **Synthetic data generation** for scalable training
- **INT8 quantization** for efficient deployment
- **Comprehensive evaluation** metrics

## Quick Start

### 1. Generate Synthetic Training Data

```bash
python -m finscribe.synthetic.export generate_dataset \
    --num-samples 8000 \
    --output-dir data/synthetic_invoices
```

### 2. Prepare Training Dataset

```bash
python -m finscribe.data.build_dataset \
    --crops-dir data/crops \
    --annotations-dir data/annotations \
    --output data/training_dataset.jsonl
```

### 3. Train Model

```bash
python train_finscribe_vl.py \
    --data-dir data \
    --output-dir ./finetuned_finscribe_vl \
    --epochs 4 \
    --batch-size 4 \
    --use-lora \
    --learning-rate 2e-5
```

### 4. Quantize for Deployment

```python
from finscribe.deploy.quantize import quantize_model
from pathlib import Path

quantize_model(
    model_path=Path("./finetuned_finscribe_vl"),
    output_path=Path("./finetuned_finscribe_vl_int8"),
)
```

### 5. Evaluate

```bash
python compare_base_vs_finetuned.py \
    --image data/test_invoice.png \
    --model ./finetuned_finscribe_vl \
    --output results.json
```

## Architecture

```
finscribe/
├── data/              # Dataset preparation
│   ├── schema.py      # Data schemas
│   ├── formatters.py  # Instruction formatting
│   └── build_dataset.py
├── training/          # Training modules
│   ├── collate.py     # Completion-only collator
│   ├── model.py       # Model loading
│   └── lora.py        # LoRA support
├── eval/              # Evaluation metrics
│   ├── field_accuracy.py
│   ├── validation.py
│   └── teds.py
├── mining/            # Hard-sample mining
│   ├── error_logger.py
│   ├── error_classifier.py
│   └── replay_dataset.py
├── synthetic/         # Synthetic data generation
│   ├── generator.py
│   ├── renderer.py
│   └── export.py
└── deploy/            # Deployment utilities
    └── quantize.py
```

## Key Features

### Completion-Only Training

The `collate_fn` masks loss on prompt tokens, ensuring the model only learns from assistant responses. This is critical for proper instruction tuning.

### Hard-Sample Mining

Automatically identifies and logs error cases for replay training:

```python
from finscribe.mining import log_error, classify_error

error_type = classify_error(pred, gt)
log_error(image_path, gt, pred, error_type)
```

### Synthetic Data Generation

Generates perfectly labeled invoices with exact arithmetic:

```python
from finscribe.synthetic import generate_invoice, render_invoice

data = generate_invoice(num_items=5, currency="USD")
image = render_invoice(data)
```

## Training Configuration

Recommended settings:

- **Epochs**: 3-5
- **Batch Size**: 4 per device
- **Gradient Accumulation**: 4 steps (effective batch size: 16)
- **Learning Rate**: 2e-5
- **LoRA Rank**: 16 (if using LoRA)
- **Mixed Precision**: bfloat16

## Evaluation Metrics

- **Field Accuracy**: Percentage of correctly extracted fields
- **TEDS Score**: Table structure recognition accuracy
- **Numeric Accuracy**: Precision of numeric extractions
- **Validation Pass Rate**: Percentage of documents passing arithmetic validation

## Performance

See `BENCHMARK_TABLE.md` for detailed results. Key improvements:

- +17.4% field extraction accuracy
- +23.5 TEDS score improvement
- 2.6x faster inference with INT8 quantization
- 60% VRAM reduction

## License

MIT


