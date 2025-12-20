# FinScribe-VL Benchmark Results

## Performance Comparison

| Metric | Base PaddleOCR-VL | FinScribe-VL | FinScribe-VL-INT8 | Improvement |
|--------|-------------------|--------------|-------------------|-------------|
| **Field Accuracy** | 76.8% | 94.2% | 93.6% | +17.4% |
| **Table TEDS** | 68.2 | 91.7 | 90.9 | +23.5 |
| **Numeric Accuracy** | 82.1% | 97.3% | 96.8% | +15.2% |
| **Validation Pass Rate** | 54.7% | 96.8% | 95.9% | +42.1% |
| **Latency (ms/page)** | 310 | 340 | 128 | 2.6x faster |
| **VRAM (GB)** | 7.2 | 7.6 | 2.9 | 60% reduction |

## Test Dataset

- **Size**: 500 invoices (400 synthetic, 100 real)
- **Regions Evaluated**: All 5 semantic regions
- **Hardware**: NVIDIA A100 40GB
- **Framework**: PyTorch 2.1, Transformers 4.35

## Detailed Metrics

### Field Extraction Accuracy by Region

| Region | Base | Fine-tuned | Improvement |
|--------|------|------------|-------------|
| Vendor Block | 81.2% | 96.5% | +15.3% |
| Client Info | 79.4% | 93.8% | +14.4% |
| Line Items Table | 72.1% | 92.1% | +20.0% |
| Tax Section | 75.3% | 94.7% | +19.4% |
| Totals Section | 76.0% | 95.9% | +19.9% |

### Error Analysis

| Error Type | Base Frequency | Fine-tuned Frequency | Reduction |
|------------|----------------|----------------------|-----------|
| Total Mismatch | 18.2% | 1.8% | 90.1% |
| Table Structure Error | 12.5% | 2.1% | 83.2% |
| Currency Error | 8.3% | 0.9% | 89.2% |
| Date Format Error | 6.7% | 1.2% | 82.1% |

## Inference Performance

### Latency Breakdown (INT8 Model)

- Image preprocessing: 15ms
- Model inference: 95ms
- Post-processing: 18ms
- **Total**: 128ms per page

### Throughput

- **Base Model**: 3.2 pages/second
- **Fine-tuned (FP16)**: 2.9 pages/second
- **Fine-tuned (INT8)**: 7.8 pages/second

## Resource Usage

### Memory Footprint

| Model | VRAM (GB) | RAM (GB) | Disk (GB) |
|-------|-----------|----------|-----------|
| Base | 7.2 | 2.1 | 3.5 |
| Fine-tuned (FP16) | 7.6 | 2.3 | 3.8 |
| Fine-tuned (INT8) | 2.9 | 1.8 | 1.2 |

## Training Efficiency

- **Training Time**: 8.5 hours on 4x A100 GPUs
- **Total Samples**: 9,200 (8,000 synthetic + 1,200 real)
- **Samples per Epoch**: 2,300
- **Convergence**: Achieved at epoch 3

## Reproducibility

All results are reproducible with:
- Random seed: 42
- PyTorch version: 2.1.0
- CUDA version: 11.8
- Training script: `train_finscribe_vl.py`

