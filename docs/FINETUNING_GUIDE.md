# PaddleOCR-VL Fine-Tuning Guide

Complete guide for fine-tuning PaddleOCR-VL-0.9B for financial document intelligence.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Data Preparation](#data-preparation)
4. [Training](#training)
5. [Evaluation](#evaluation)
6. [Hard-Sample Mining](#hard-sample-mining)
7. [Quantization](#quantization)
8. [Deployment](#deployment)

## Overview

This fine-tuning system specializes PaddleOCR-VL-0.9B for extracting structured data from financial documents. The approach uses:

- **Supervised Fine-Tuning (SFT)** with completion-only loss masking
- **LoRA** for memory-efficient training
- **Hard-sample mining** for iterative improvement
- **INT8 quantization** for deployment efficiency

## Prerequisites

### Hardware

- **Minimum**: 1x GPU with 16GB VRAM (e.g., RTX 3090, A4000)
- **Recommended**: 1x GPU with 24GB+ VRAM (e.g., A100, RTX 4090)
- **Optimal**: 4x A100 40GB for faster training

### Software

```bash
pip install -r requirements.txt
```

Key dependencies:
- PyTorch >= 2.1.0
- Transformers >= 4.35.0
- PEFT >= 0.6.0 (for LoRA)
- Datasets >= 2.14.0

## Data Preparation

### Step 1: Generate Synthetic Data

Synthetic invoices provide perfect ground truth with exact arithmetic:

```bash
python examples/generate_training_data.py
```

Or programmatically:

```python
from finscribe.synthetic.export import generate_dataset
from pathlib import Path

generate_dataset(
    num_samples=8000,
    output_dir=Path("data/synthetic_invoices"),
)
```

### Step 2: Prepare Real Data (Optional)

If you have real invoices:

1. **Crop semantic regions** using PP-DocLayoutV2 or rule-based logic
2. **Annotate** each crop with ground truth JSON
3. **Organize** into `crops/` and `annotations/` directories

Annotation format:

```json
{
  "region": "vendor_block",
  "fields": {
    "vendor_name": "ABC Corp",
    "address": "123 Main St",
    "tax_id": "US123456789"
  }
}
```

### Step 3: Build Training Dataset

```python
from finscribe.data.build_dataset import build_dataset
from pathlib import Path

dataset = build_dataset(
    crops_dir=Path("data/crops"),
    annotations_dir=Path("data/annotations"),
)
```

Or from manifest:

```python
from finscribe.data.build_dataset import build_dataset_from_manifest

dataset = build_dataset_from_manifest(
    manifest_path=Path("data/training_manifest.json"),
)
```

## Training

### Basic Training

```bash
python train_finscribe_vl.py \
    --data-dir data \
    --output-dir ./finetuned_finscribe_vl \
    --epochs 4 \
    --batch-size 4 \
    --gradient-accumulation-steps 4 \
    --learning-rate 2e-5
```

### With LoRA (Memory-Efficient)

```bash
python train_finscribe_vl.py \
    --data-dir data \
    --output-dir ./finetuned_finscribe_vl \
    --epochs 4 \
    --batch-size 4 \
    --use-lora \
    --lora-r 16 \
    --learning-rate 2e-5
```

### Training Configuration

| Parameter | Recommended Value | Notes |
|-----------|-------------------|-------|
| Epochs | 3-5 | Start with 3, increase if underfitting |
| Batch Size | 4 | Adjust based on GPU memory |
| Gradient Accumulation | 4 | Effective batch size = 16 |
| Learning Rate | 2e-5 | Standard for SFT |
| LoRA Rank | 16 | Higher = more parameters, better quality |
| Warmup Ratio | 0.1 | 10% of steps for warmup |

### Monitoring Training

Training logs include:
- Loss per step
- Learning rate schedule
- Checkpoint saves every 500 steps

## Evaluation

### Single Sample Evaluation

```bash
python examples/evaluate_model.py \
    --image data/test_invoice.png \
    --ground-truth data/test_invoice.json \
    --model ./finetuned_finscribe_vl \
    --output results.json
```

### Batch Evaluation

```python
from finscribe.eval.field_accuracy import field_accuracy
from finscribe.eval.validation import validate_document

# Evaluate each sample
accuracies = []
for sample in test_dataset:
    accuracy = field_accuracy(sample["pred"], sample["gt"])
    accuracies.append(accuracy)

print(f"Average Accuracy: {sum(accuracies) / len(accuracies):.2%}")
```

### Comparison Script

Compare base vs fine-tuned:

```bash
python compare_base_vs_finetuned.py \
    --image data/test_invoice.png \
    --model ./finetuned_finscribe_vl \
    --output comparison.json
```

## Hard-Sample Mining

### Automatic Error Logging

During inference, log errors:

```python
from finscribe.mining import log_error, classify_error

# After inference
error_type = classify_error(pred, gt)
if error_type != "OTHER":
    log_error(image_path, gt, pred, error_type)
```

### Replay Training

Build dataset from logged errors:

```python
from finscribe.mining.replay_dataset import build_hard_sample_dataset
from pathlib import Path

hard_samples = build_hard_sample_dataset(
    error_dir=Path("data/hard_samples"),
    region_type="totals_section",
)

# Mix with normal data (80% normal, 20% hard)
normal_dataset = build_dataset(...)
combined = normal_dataset + hard_samples[:len(normal_dataset) // 4]
```

## Quantization

### INT8 Quantization

Reduce model size and latency:

```python
from finscribe.deploy.quantize import quantize_model
from pathlib import Path

quantize_model(
    model_path=Path("./finetuned_finscribe_vl"),
    output_path=Path("./finetuned_finscribe_vl_int8"),
)
```

**Requirements**: `pip install optimum[onnxruntime]`

### Performance Impact

- **VRAM**: ~60% reduction (7.6GB → 2.9GB)
- **Latency**: 2.6x faster (340ms → 128ms)
- **Accuracy**: <1% drop (94.2% → 93.6%)

## Deployment

### Load Quantized Model

```python
from finscribe.deploy.quantize import load_quantized_model
from pathlib import Path

model = load_quantized_model(Path("./finetuned_finscribe_vl_int8"))
```

### Integration with Existing Service

Update `PaddleOCRVLService` to use fine-tuned model:

```python
# In app/core/models/paddleocr_vl_service.py
model = AutoModelForCausalLM.from_pretrained(
    "./finetuned_finscribe_vl_int8",
    trust_remote_code=True,
)
```

## Troubleshooting

### Out of Memory

- Reduce batch size: `--batch-size 2`
- Use LoRA: `--use-lora`
- Reduce gradient accumulation: `--gradient-accumulation-steps 2`

### Poor Accuracy

- Increase training data (aim for 10k+ samples)
- Enable hard-sample mining
- Increase LoRA rank: `--lora-r 32`
- Train for more epochs: `--epochs 5`

### Slow Training

- Enable Flash Attention (automatic if available)
- Use multiple GPUs with `accelerate`
- Reduce logging frequency: `--logging-steps 50`

## Best Practices

1. **Start with synthetic data** - Perfect labels help model learn structure
2. **Use LoRA** - Faster training, easier to iterate
3. **Monitor validation** - Track accuracy on held-out set
4. **Mine hard samples** - Focus training on failure cases
5. **Quantize for production** - INT8 provides best speed/size tradeoff

## Next Steps

- See `MODEL_CARD.md` for model details
- See `BENCHMARK_TABLE.md` for performance metrics
- See `finscribe/README.md` for API documentation

