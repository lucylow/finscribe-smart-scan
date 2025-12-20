# Phase 2: Fine-Tuning Strategy for PaddleOCR-VL

This directory contains the implementation of Phase 2 fine-tuning strategy for PaddleOCR-VL, focusing on teaching the model to recognize and extract **5 key semantic regions** from invoices:

## 🆕 Semantic Understanding Training

**NEW**: We now support **semantic understanding training** that teaches the model to understand document structure and logic, not just extract text. See **[SEMANTIC_TRAINING_GUIDE.md](./SEMANTIC_TRAINING_GUIDE.md)** for complete instructions.

The semantic approach uses **instruction fine-tuning** with diverse prompt types:
- **Field Extraction**: Extract specific fields on demand
- **Full JSON Parsing**: Parse entire documents into structured JSON
- **Table Reconstruction**: Convert tables to CSV/JSON formats
- **Logical Reasoning**: Verify arithmetic and validate consistency
- **Summarization**: Provide concise document summaries

Use `create_semantic_instruction_pairs.py` to generate training data with these instruction types.

---

## Original Approach: Semantic Region Extraction

The original approach focuses on teaching the model to recognize and extract **5 key semantic regions** from invoices:

1. **Vendor Block** (name, address, contact)
2. **Client/Invoice Info** (date, number, due date)
3. **Line Item Table** (description, quantity, price, total)
4. **Tax & Discount Section**
5. **Grand Total & Payment Terms**

## Overview

This phase implements **Supervised Fine-Tuning (SFT)** with **LoRA** (Low-Rank Adaptation) for efficient training. The approach transforms synthetic invoice data from Phase 1 into instruction-response pairs that teach the model semantic region extraction.

## Directory Structure

```
phase2_finetuning/
├── create_instruction_pairs.py  # Convert Phase 1 data to instruction pairs
├── finetune_config.yaml          # Training configuration
├── train_finetune.py             # Main training script
├── weighted_loss.py              # Custom loss with table cell weighting
├── evaluation_metrics.py         # Region-specific evaluation metrics
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Quick Start

### 1. Install Dependencies

```bash
cd phase2_finetuning
pip install -r requirements.txt
```

### 2. Prepare Training Data

**Option A: Semantic Understanding Training (Recommended)**

Generate diverse instruction pairs for semantic understanding:

```bash
# Generate semantic instruction pairs with all 5 instruction types
python create_semantic_instruction_pairs.py \
    --manifest ../synthetic_invoice_generator/output/training_manifest.json \
    --output semantic_instruction_pairs.jsonl

# Or generate only specific types
python create_semantic_instruction_pairs.py \
    --manifest ../synthetic_invoice_generator/output/training_manifest.json \
    --output semantic_instruction_pairs.jsonl \
    --include-types field_extraction full_json_parsing
```

**Option B: Original Semantic Region Extraction**

Convert your Phase 1 synthetic invoice data into instruction-response pairs:

```bash
# Using training manifest from Phase 1
python create_instruction_pairs.py \
    --manifest ../synthetic_invoice_generator/output/training_manifest.json \
    --output paddleocr_finetune_data.jsonl

# OR using directories directly
python create_instruction_pairs.py \
    --ground-truth-dir ../synthetic_invoice_generator/output/ground_truth \
    --images-dir ../synthetic_invoice_generator/output/images \
    --output paddleocr_finetune_data.jsonl
```

This creates a JSONL file with instruction-response pairs, where each invoice generates 4-5 pairs (one for each semantic region).

### 3. Configure Training

Edit `finetune_config.yaml` to adjust:
- Model path
- Dataset path
- LoRA parameters (rank, alpha, target modules)
- Training hyperparameters (learning rate, batch size, epochs)
- Loss weighting (table cell vs regular token weights)

### 4. Run Training

**For semantic understanding training (recommended):**

```bash
python train_finetune_enhanced.py \
    --config finetune_config.yaml \
    --dataset semantic_instruction_pairs.jsonl
```

**For original semantic region extraction:**

```bash
python train_finetune.py --config finetune_config.yaml
```

**Quick start script:**

```bash
./example_semantic_training.sh
```

**Note**: The training script is a framework that may need adaptation based on the actual PaddleOCR-VL/ERNIEKit API. See "Integration Notes" below.

## Key Components

### Instruction-Response Pair Generation

`create_instruction_pairs.py` converts invoice metadata into training pairs:

- **Prompt format**: `"<image>\nExtract the vendor information from this invoice."`
- **Response format**: JSON with region identifier and structured content
- **Multiple pairs per invoice**: One for each semantic region

Example pair:
```json
{
  "image": "path/to/invoice.png",
  "conversations": [
    {"role": "human", "content": "<image>\nExtract the vendor information..."},
    {"role": "assistant", "content": "{\"region\": \"vendor_block\", \"content\": {...}}"}
  ]
}
```

### LoRA Configuration

LoRA (Low-Rank Adaptation) is used for efficient fine-tuning:

- **Rank (r)**: 16 (adjustable based on model size)
- **Alpha**: 32 (typically 2x rank)
- **Target modules**: Attention projection layers (`q_proj`, `v_proj`, etc.)
- **Benefits**: Fast training, low memory usage, preserves base model knowledge

### Weighted Loss Function

`weighted_loss.py` implements special loss weighting:

- **Table cell tokens**: Higher weight (2.0x default) for better table extraction
- **Field-level weights**: Different weights per semantic region
- **Customizable**: Configure via `finetune_config.yaml`

### Evaluation Metrics

`evaluation_metrics.py` provides region-specific evaluation:

1. **Field Extraction Accuracy**: Per-region accuracy (vendor, client info, financial summary)
2. **Table Structure Accuracy (TEDS)**: Evaluates table row/column/cell accuracy
3. **Numerical Validation**: Checks mathematical consistency (subtotal + tax - discount = grand_total)

Run evaluation:
```python
from evaluation_metrics import evaluate_sample, evaluate_dataset

# Evaluate single sample
result = evaluate_sample(predicted_json_string, ground_truth_dict)

# Evaluate entire dataset
aggregated = evaluate_dataset(predictions_list, ground_truths_list)
```

## Training Configuration

Key parameters in `finetune_config.yaml`:

### LoRA Settings
```yaml
lora:
  enabled: true
  r: 16                    # LoRA rank
  lora_alpha: 32          # Scaling parameter
  target_modules: ["q_proj", "v_proj", "k_proj", "o_proj"]
```

### Training Hyperparameters
```yaml
training:
  num_train_epochs: 5
  per_device_train_batch_size: 4
  learning_rate: 2.0e-4
  warmup_steps: 100
```

### Loss Weighting
```yaml
loss:
  weighted: true
  weights:
    table_cell_token: 2.0
    regular_token: 1.0
  field_weights:
    line_item_table: 2.5
    financial_summary: 2.0
```

### Data Augmentation
```yaml
vision_processor:
  train:
    additional_transforms:
      - name: "RandomRotation"
        degrees: [-5, 5]
      - name: "RandomGaussianNoise"
        std: [0.01, 0.05]
```

## Integration Notes

### PaddleOCR-VL / ERNIEKit Integration

The training script (`train_finetune.py`) uses standard HuggingFace Transformers APIs as a framework. However, PaddleOCR-VL may use:

1. **Custom model classes**: Adjust imports to use PaddleOCR-VL-specific classes
2. **ERNIEKit training framework**: May require using ERNIEKit's training scripts instead
3. **Custom processors**: Vision-language processors may differ from standard AutoProcessor

**Recommended approach**:
- If using ERNIEKit, adapt the configuration format to ERNIEKit's expected format
- Use ERNIEKit's training scripts with the instruction pairs as input
- Apply LoRA via ERNIEKit's LoRA support (if available) or PEFT library

### GPU Requirements

- **Recommended**: NVIDIA GPU with 16GB+ VRAM
- **Minimum**: 8GB VRAM (with smaller batch size)
- **Batch size**: Adjust `per_device_train_batch_size` based on available memory

### Training Time Estimates

- **Small dataset** (1K invoices): ~1-2 hours on single GPU
- **Medium dataset** (5K invoices): ~4-6 hours
- **Large dataset** (10K+ invoices): ~8-12 hours

## Evaluation Strategy

### During Training

- Validation loss is tracked automatically
- Checkpoints saved every N steps (configurable)
- Best model based on validation loss is saved

### After Training

Evaluate on held-out test set:

```python
from evaluation_metrics import evaluate_dataset

# Load test predictions and ground truth
predictions = [...]  # List of JSON strings from model
ground_truths = [...]  # List of metadata dicts

results = evaluate_dataset(predictions, ground_truths)
print(f"Vendor block accuracy: {results['region_accuracies']['vendor_block']['mean']:.2%}")
print(f"Table TEDS score: {results['table_accuracy']['mean_teds']:.2%}")
print(f"Numerical validation rate: {results['numerical_validation']['valid_rate']:.2%}")
```

### Region-Specific Thresholds

Configure evaluation thresholds in `finetune_config.yaml`:

```yaml
evaluation:
  thresholds:
    vendor_block: 0.95
    client_invoice_info: 0.95
    line_item_table: 0.90
    financial_summary: 0.95
```

## Advanced Topics

### Custom Loss Implementation

To implement more sophisticated loss weighting:

1. Modify `weighted_loss.py` to parse response structure
2. Map tokens to fields using token position information
3. Apply field-specific weights dynamically

### Data Augmentation Pipeline

Current augmentation is configured but requires implementation:

1. Use `torchvision.transforms` or `albumentations`
2. Apply augmentations in dataset `__getitem__` method
3. Balance augmentation strength (too much can hurt performance)

### Multi-GPU Training

Use HuggingFace Accelerate or PyTorch DDP:

```bash
# With accelerate
accelerate config  # Configure multi-GPU setup
accelerate launch train_finetune.py --config finetune_config.yaml

# With torchrun
torchrun --nproc_per_node=4 train_finetune.py --config finetune_config.yaml
```

## Troubleshooting

### Out of Memory Errors

- Reduce `per_device_train_batch_size`
- Increase `gradient_accumulation_steps` to maintain effective batch size
- Enable `fp16` (mixed precision training)
- Reduce LoRA rank (`r`)

### Poor Performance

- Check data quality (instruction pairs correctly formatted)
- Verify image paths are correct
- Increase training epochs
- Adjust learning rate (try 1e-4 to 5e-4)
- Review loss weighting configuration

### Model Not Converging

- Verify loss is decreasing (check TensorBoard logs)
- Ensure sufficient warmup steps
- Check learning rate schedule
- Validate ground truth data format

## Next Steps

After Phase 2:

1. **Evaluate** on test set with region-specific metrics
2. **Iterate** on hyperparameters based on results
3. **Fine-tune** loss weights if specific regions underperform
4. **Deploy** fine-tuned model for inference
5. **Monitor** performance on real-world invoices
6. **Active Learning**: Collect misclassified samples for Phase 3

## References

- [LoRA Paper](https://arxiv.org/abs/2106.09685)
- [PaddleOCR-VL Documentation](https://github.com/PaddlePaddle/PaddleOCR)
- [ERNIEKit](https://github.com/PaddlePaddle/ERNIEKit)
- [HuggingFace PEFT](https://huggingface.co/docs/peft)

