# Training Quick Start Guide
## PaddleOCR-VL Fine-Tuning for Financial Documents

This guide walks you through the complete training pipeline for fine-tuning PaddleOCR-VL on financial documents.

## Prerequisites

1. **Python Environment**: Python 3.8+
2. **GPU**: NVIDIA GPU with 16GB+ VRAM (8GB minimum with smaller batch size)
3. **Dependencies**: Install required packages (see below)

## Step 1: Install Dependencies

```bash
# Install core dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers accelerate peft
pip install pillow faker reportlab
pip install pyyaml numpy

# Optional: For ERNIEKit (if available)
# pip install erniekit

# Optional: For evaluation
pip install scikit-learn editdistance
```

## Step 2: Generate Synthetic Dataset

Generate a diverse dataset of synthetic financial documents:

```bash
python -m finscribe.training.data_synthesis \
    --num-samples 10000 \
    --output-dir synthetic_data \
    --include-hard-samples
```

This creates:
- `synthetic_data/financial_documents.jsonl`: Dataset with invoice metadata
- You'll need to render these to images (see Step 3)

### Dataset Statistics
- **Regular samples**: 90% (varied complexity, layouts, currencies)
- **Hard samples**: 10% (targeting specific error types)
- **Total**: 10,000 samples (adjustable)

## Step 3: Render Documents to Images

You need to render the synthetic invoice data to actual images. Use your existing synthetic invoice generator:

```bash
# If you have the synthetic_invoice_generator
python synthetic_invoice_generator/generate_dataset.py \
    --num-samples 10000 \
    --output-dir synthetic_data/images \
    --ground-truth-dir synthetic_data/ground_truth
```

Or use the existing generator in `finscribe/synthetic/generator.py` and create a rendering script.

## Step 4: Create Instruction Pairs

Convert your dataset to instruction-response pairs for fine-tuning:

```bash
python -m finscribe.training.instruction_pairs \
    --dataset synthetic_data/financial_documents.jsonl \
    --images-dir synthetic_data/images \
    --output training_data/instruction_pairs.jsonl \
    --pairs-per-sample 5
```

This creates instruction pairs where each document generates 5 training examples:
- Full document extraction
- Vendor block extraction
- Client info extraction
- Line items extraction
- Financial summary extraction

## Step 5: Split Dataset

Split your data into train/validation/test sets:

```bash
python -c "
import json
import random
from pathlib import Path

# Load data
with open('training_data/instruction_pairs.jsonl', 'r') as f:
    data = [json.loads(line) for line in f if line.strip()]

# Shuffle
random.shuffle(data)

# Split: 80% train, 10% val, 10% test
n = len(data)
train = data[:int(0.8*n)]
val = data[int(0.8*n):int(0.9*n)]
test = data[int(0.9*n):]

# Save
for split, name in [(train, 'train'), (val, 'validation'), (test, 'test')]:
    with open(f'training_data/{name}_pairs.jsonl', 'w') as f:
        for item in split:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f'Saved {len(split)} samples to training_data/{name}_pairs.jsonl')
"
```

## Step 6: Configure Training

Edit `finscribe/training/config.yaml` to adjust:
- **Learning rate**: Start with 2e-5, adjust based on loss
- **Batch size**: Maximum your GPU can handle (typically 4-16)
- **Epochs**: 3-5 (monitor for overfitting)
- **LoRA settings**: Adjust rank (r) and alpha if needed

Key parameters (from PaddleOCR guidance):
- **Learning Rate**: 1e-5 to 5e-5 (critical parameter)
- **Batch Size**: Maximum GPU can handle
- **Warmup Steps**: 10% of total steps

## Step 7: Run Training

### Option A: Using ERNIEKit (Recommended if available)

```bash
python -m finscribe.training.erniekit_train \
    --data training_data/instruction_pairs.jsonl \
    --config finscribe/training/config.yaml
```

### Option B: Using HuggingFace Transformers + PEFT (Fallback)

```bash
# Use the existing phase2_finetuning script
python phase2_finetuning/train_finetune.py \
    --config finscribe/training/config.yaml
```

### Training Progress

Monitor training:
- **Loss**: Should decrease steadily
- **Validation Loss**: Should track training loss (watch for overfitting)
- **Checkpoints**: Saved every 500 steps to `outputs/finetuned_model/`

Expected training time:
- **10K samples**: 2-4 hours on single GPU
- **50K samples**: 8-12 hours
- **100K+ samples**: 16-24 hours

## Step 8: Evaluate Model

Evaluate on test set:

```bash
python -m finscribe.training.evaluation \
    --model outputs/finetuned_model \
    --test-data training_data/test_pairs.jsonl \
    --output evaluation_results.json
```

Metrics:
- **Field Extraction Accuracy**: Per-field accuracy
- **Table TEDS Score**: Table structure accuracy
- **Numerical Validation**: Mathematical consistency
- **F1 Score**: Overall performance

## Step 9: Hard Sample Mining (Iterative Improvement)

After initial training, identify failure cases:

```bash
# Run predictions on validation set
python -m finscribe.training.predict \
    --model outputs/finetuned_model \
    --data training_data/validation_pairs.jsonl \
    --output predictions.jsonl

# Mine hard samples
python -m finscribe.training.hard_sample_mining \
    --predictions predictions.jsonl \
    --ground-truth training_data/validation_pairs.jsonl \
    --output hard_samples_analysis.json
```

This identifies:
- Samples with 3+ errors (hard samples)
- Error patterns by element type
- Synthesis plan for targeted improvement

## Step 10: Iterate

1. **Generate hard samples**: Use synthesis plan to create targeted samples
2. **Add to training set**: Combine with existing data
3. **Retrain**: Run training again with updated dataset
4. **Evaluate**: Check if metrics improved
5. **Repeat**: Until validation metrics plateau

## Troubleshooting

### Out of Memory Errors

- Reduce `per_device_train_batch_size` in config
- Increase `gradient_accumulation_steps` to maintain effective batch size
- Enable `fp16` or `bf16` (mixed precision)
- Reduce LoRA rank (`r` in config)
- Enable `gradient_checkpointing`

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

After successful training:

1. **Deploy**: Integrate fine-tuned model into your application
2. **Monitor**: Track performance on real-world documents
3. **Active Learning**: Collect errors for next iteration
4. **Optimize**: Quantize model for faster inference (INT8/INT4)

## References

- [Training Strategy](./TRAINING_STRATEGY.md): Comprehensive strategy document
- [PaddleOCR-VL GitHub](https://github.com/PaddlePaddle/PaddleOCR)
- [ERNIEKit Documentation](https://github.com/PaddlePaddle/ERNIEKit)

