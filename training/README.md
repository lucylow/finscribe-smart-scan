# Training Guide: Fine-Tuning PaddleOCR-VL for Financial Documents

This guide explains how to fine-tune PaddleOCR-VL on financial documents using the FinScribe training pipeline.

## Overview

The training process fine-tunes PaddleOCR-VL-0.9B using:
- **LoRA (Low-Rank Adaptation)** for efficient parameter-efficient fine-tuning
- **Completion-Only Training** to preserve instruction-following capabilities
- **Synthetic + Real Data** for diverse training examples
- **Advanced Loss Functions** for better numeric and table accuracy

## Prerequisites

### Hardware Requirements

- **GPU**: NVIDIA GPU with 16GB+ VRAM (A100, V100, RTX 3090/4090 recommended)
- **CPU**: 8+ cores recommended for data preprocessing
- **RAM**: 32GB+ system RAM
- **Storage**: 50GB+ free space for datasets and model checkpoints

### Software Requirements

- **Python**: 3.10 or 3.11
- **CUDA**: 11.8 or 12.1 (for GPU support)
- **PyTorch**: 2.1.0 or later
- **Transformers**: 4.35.0 or later

### Environment Setup

```bash
# Clone repository
git clone https://github.com/yourusername/finscribe-smart-scan.git
cd finscribe-smart-scan

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install training-specific dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers>=4.35.0 peft>=0.6.0 accelerate>=0.24.0
pip install flash-attn --no-build-isolation  # Optional: for Flash Attention 2
```

## Dataset Preparation

### Option 1: Use Existing Dataset

The repository includes pre-generated synthetic data:

```bash
# Dataset is already in data/ directory
# Training: data/unsloth_train.jsonl
# Validation: data/unsloth_val.jsonl
```

### Option 2: Generate New Synthetic Data

```bash
# Generate 5000 synthetic invoices
python ml/synthetic_invoice_generator/src/data_generator.py \
  --output-dir data/synthetic \
  --count 5000 \
  --template-set all \
  --format jsonl
```

### Option 3: Prepare Custom Dataset

1. **Format Requirements**: Each line must be a JSON object with `instruction`, `input`, and `output` fields
2. **Schema**: Output JSON must match the canonical schema (see `data/README_data.md`)
3. **Validation**: Validate dataset before training:

```bash
python finscribe/data/validate_dataset.py \
  --input data/your_train.jsonl \
  --schema data/schema.json
```

## Configuration

### Configuration File Structure

Training is configured via YAML file (default: `phase2_finetuning/finetune_config.yaml`):

```yaml
# Model Configuration
model_name_or_path: "PaddlePaddle/PaddleOCR-VL"
dataset_path: "./data/unsloth_train.jsonl"

# LoRA Configuration
lora:
  enabled: true
  r: 16
  lora_alpha: 32
  target_modules: ["q_proj", "v_proj", "k_proj", "o_proj"]
  dropout: 0.05

# Training Hyperparameters
training:
  learning_rate: 2.0e-5
  per_device_train_batch_size: 8
  gradient_accumulation_steps: 2
  num_train_epochs: 5
  warmup_ratio: 0.1
  weight_decay: 0.01
  max_grad_norm: 1.0
  lr_scheduler_type: "cosine"
  gradient_checkpointing: true

# Output
output_dir: "./finetuned_paddleocr_invoice_model"
```

### Key Hyperparameters

| Parameter | Default | Recommended Range | Description |
|-----------|---------|-------------------|-------------|
| `learning_rate` | 2.0e-5 | 1e-5 to 5e-5 | Most critical parameter. Start conservative. |
| `per_device_train_batch_size` | 8 | 4-16 | Increase if GPU memory allows. |
| `gradient_accumulation_steps` | 2 | 1-4 | Effective batch = batch_size × accumulation_steps |
| `num_train_epochs` | 5 | 3-10 | Use early stopping to prevent overfitting. |
| `warmup_ratio` | 0.1 | 0.05-0.1 | Gradually increase LR at start. |
| `lora.r` | 16 | 8-32 | LoRA rank (higher = more capacity). |

**See `prompt_format.md` for prompt engineering details.**

## Training Process

### Basic Training Command

```bash
# Train with default configuration
python phase2_finetuning/train_finetune_enhanced.py \
  --config phase2_finetuning/finetune_config.yaml
```

### Training with Custom Dataset

```bash
# Edit finetune_config.yaml to set dataset_path, or override:
python phase2_finetuning/train_finetune_enhanced.py \
  --config phase2_finetuning/finetune_config.yaml \
  --train-file data/custom_train.jsonl \
  --val-file data/custom_val.jsonl
```

### Training with Quantization (4-bit QLoRA)

For GPUs with limited memory (< 16GB VRAM):

```bash
python phase2_finetuning/train_finetune_enhanced.py \
  --config phase2_finetuning/finetune_config.yaml \
  --use-quantization
```

**Note**: Quantization reduces memory usage by ~75% but may slightly reduce accuracy.

### Resume Training from Checkpoint

```bash
python phase2_finetuning/train_finetune_enhanced.py \
  --config phase2_finetuning/finetune_config.yaml \
  --resume ./finetuned_paddleocr_invoice_model/checkpoint-1000
```

## Training Output

### Directory Structure

```
finetuned_paddleocr_invoice_model/
├── checkpoint-500/          # Intermediate checkpoints
│   ├── adapter_config.json
│   ├── adapter_model.bin
│   └── training_state.json
├── checkpoint-1000/
├── final_model/             # Best model (loaded at end)
│   ├── adapter_config.json
│   ├── adapter_model.bin
│   └── ...
├── logs/                    # Training logs (TensorBoard format)
└── runs/                    # Weights & Biases logs (if configured)
```

### Monitoring Training

#### TensorBoard

```bash
# Start TensorBoard
tensorboard --logdir finetuned_paddleocr_invoice_model/logs

# View at http://localhost:6006
```

**Key Metrics to Monitor:**
- `train_loss`: Should decrease steadily
- `eval_loss`: Should decrease and track train_loss
- `eval_field_accuracy`: Field extraction accuracy on validation set
- `eval_teds_score`: Table structure accuracy (TEDS metric)

#### Console Output

Training progress is logged to console with:
- Loss values (every `logging_steps`)
- Evaluation metrics (every `eval_steps`)
- Model checkpoints saved (every `save_steps`)

**Example Output:**
```
{'loss': 2.345, 'learning_rate': 0.000018, 'epoch': 0.5}
{'eval_loss': 1.892, 'eval_field_accuracy': 0.876, 'eval_teds_score': 0.845, 'epoch': 0.5}
```

## Hyperparameter Tuning

### Learning Rate Finder

Use the learning rate finder to identify optimal learning rate:

```bash
python phase2_finetuning/learning_rate_finder.py \
  --config phase2_finetuning/finetune_config.yaml \
  --output lr_finder_results.png
```

**Interpretation**: Look for the steepest downward slope in loss. Use a learning rate slightly lower than the point where loss starts increasing.

### A/B Testing Hyperparameters

Change **one parameter at a time** and compare results:

```bash
# Experiment 1: Lower learning rate
# Edit finetune_config.yaml: learning_rate: 1.0e-5
python phase2_finetuning/train_finetune_enhanced.py --config phase2_finetuning/finetune_config.yaml

# Experiment 2: Higher learning rate
# Edit finetune_config.yaml: learning_rate: 3.0e-5
python phase2_finetuning/train_finetune_enhanced.py --config phase2_finetuning/finetune_config.yaml
```

### Early Stopping

Training automatically stops if validation loss doesn't improve for `patience` epochs (configurable in config file).

**Manual Early Stopping**: Press `Ctrl+C` to stop training gracefully. Latest checkpoint is saved.

## Advanced Features

### Advanced Loss Functions

Enable focal loss or label smoothing in `finetune_config.yaml`:

```yaml
loss:
  use_focal: true
  focal_alpha: 1.0
  focal_gamma: 2.0
  # OR
  use_label_smoothing: true
  label_smoothing: 0.1
```

### Advanced Augmentation

Data augmentation is applied on-the-fly during training. Configure in `finetune_config.yaml`:

```yaml
augmentation:
  enabled: true
  rotation_range: [-5, 5]
  brightness_range: [0.8, 1.2]
  contrast_range: [0.8, 1.2]
  noise_std: [0.01, 0.05]
  blur_probability: 0.1
```

### Curriculum Learning

Gradually increase difficulty during training:

```bash
python phase2_finetuning/curriculum_learning.py \
  --config phase2_finetuning/finetune_config.yaml \
  --difficulty-schedule easy_to_hard
```

## Evaluation

### Evaluate Trained Model

```bash
python ml/examples/evaluate_model.py \
  --test-dir data/test_dataset \
  --model-path ./finetuned_paddleocr_invoice_model/final_model \
  --output evaluation/results.json
```

**Expected Output:**
```
Field Accuracy: 94.2%
TEDS Score: 91.7%
Numeric Accuracy: 97.3%
Validation Pass Rate: 96.8%
```

### Compare Baseline vs Fine-Tuned

```bash
python ml/training/compare_base_vs_finetuned_enhanced.py \
  --baseline-model PaddlePaddle/PaddleOCR-VL \
  --finetuned-model ./finetuned_paddleocr_invoice_model/final_model \
  --test-dir data/test_dataset \
  --output evaluation/comparison_report.md
```

## Troubleshooting

### Out of Memory (OOM) Errors

**Solutions:**
1. Reduce `per_device_train_batch_size` (e.g., from 8 to 4)
2. Enable gradient checkpointing: `gradient_checkpointing: true`
3. Use quantization: `--use-quantization`
4. Reduce `max_seq_length` in config

### Loss Not Decreasing

**Possible Causes:**
1. Learning rate too high → Reduce by 2-5x
2. Learning rate too low → Increase by 2x
3. Dataset quality issues → Validate dataset
4. Overfitting → Reduce epochs, increase weight_decay

### NaN Loss Values

**Solutions:**
1. Reduce learning rate significantly (e.g., by 10x)
2. Enable gradient clipping: `max_grad_norm: 1.0`
3. Check for invalid data in dataset

### Slow Training

**Optimizations:**
1. Enable Flash Attention 2 (if supported)
2. Use mixed precision training: `bf16: true` (if GPU supports it)
3. Increase batch size (if memory allows)
4. Use gradient accumulation instead of larger batches

## Best Practices

1. **Start Conservative**: Use default hyperparameters initially, then tune
2. **Monitor Validation Metrics**: Watch for overfitting (train_loss decreasing but eval_loss increasing)
3. **Save Checkpoints Frequently**: Enable checkpointing every 500-1000 steps
4. **Use Early Stopping**: Prevent overfitting by stopping when validation loss plateaus
5. **Validate Dataset**: Ensure dataset quality before training
6. **Version Control**: Tag model checkpoints with git commits or version numbers

## Production Deployment

After training, the model can be deployed:

```bash
# Merge LoRA adapters into base model (for standalone deployment)
python ml/examples/merge_lora/merge_adapters.py \
  --base-model PaddlePaddle/PaddleOCR-VL \
  --adapter-path ./finetuned_paddleocr_invoice_model/final_model \
  --output-dir ./deployed_model

# Or use LoRA adapters directly (smaller files, requires base model)
# Just copy adapter files to deployment location
```

## Next Steps

- See `evaluation/results.md` for detailed evaluation results
- See `prompt_format.md` for prompt engineering details
- See `data/README_data.md` for dataset documentation
- See main `README.md` for inference and API usage

## Additional Resources

- [PaddleOCR-VL Documentation](https://github.com/PaddlePaddle/PaddleOCR)
- [LoRA Paper](https://arxiv.org/abs/2106.09685)
- [Hugging Face Transformers Documentation](https://huggingface.co/docs/transformers)

