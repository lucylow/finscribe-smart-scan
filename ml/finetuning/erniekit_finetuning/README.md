# ERNIE Fine-Tuning with ERNIEKit

This directory contains tools for fine-tuning ERNIE models using **LoRA (Low-Rank Adaptation)** for financial document reasoning.

## Overview

Fine-tuning ERNIE models allows you to:
- **Customize output format** for your specific JSON structure
- **Teach domain-specific rules** (financial validation, arithmetic checks)
- **Improve accuracy** on financial document reasoning tasks
- **Reduce API costs** by running models locally

## Prerequisites

### Hardware Requirements

- **Minimum**: 1x GPU with 16GB VRAM (for ERNIE-4.5-8B)
- **Recommended**: 1x GPU with 24GB+ VRAM (for ERNIE-4.5-8B with LoRA)
- **For ERNIE-4.5-VL-28B**: 4x A100 40GB or equivalent (requires ~80GB to load)

### Software Requirements

```bash
# Install dependencies
pip install transformers peft datasets torch accelerate
pip install pyyaml  # For config files

# If using ERNIEKit (official PaddlePaddle toolkit)
# Follow ERNIEKit installation guide: https://github.com/PaddlePaddle/ERNIEKit
```

## Quick Start

### Step 1: Prepare Training Data

Convert your data into instruction-response pairs:

```bash
# From active learning data
python erniekit_finetuning/prepare_data.py \
    --active-learning-file ../active_learning.jsonl \
    --output ernie_finetune_data.jsonl

# OR from synthetic invoice data
python erniekit_finetuning/prepare_data.py \
    --manifest ../synthetic_invoice_generator/output/training_manifest.json \
    --images-dir ../synthetic_invoice_generator/output/images \
    --ground-truth-dir ../synthetic_invoice_generator/output/ground_truth \
    --output ernie_finetune_data.jsonl
```

### Step 2: Configure Training

Edit `erniekit_config.yaml` to adjust:
- Model name (use smaller model like ERNIE-4.5-8B for fine-tuning)
- LoRA parameters (rank, alpha, target modules)
- Training hyperparameters (learning rate, batch size, epochs)

### Step 3: Train with LoRA

```bash
python erniekit_finetuning/train_ernie_lora.py \
    --config erniekit_config.yaml \
    --dataset ernie_finetune_data.jsonl \
    --output-dir ./finetuned_ernie
```

**Note**: The training script (`train_ernie_lora.py`) uses standard HuggingFace APIs as a framework. You may need to adapt it based on:
- ERNIE model availability on HuggingFace
- ERNIEKit's specific APIs (if using official toolkit)
- Custom model loading requirements

## Data Format

### Instruction-Response Pairs

Each training sample should be a JSON object with this structure:

```json
{
  "image": "path/to/invoice.png",
  "conversations": [
    {
      "role": "human",
      "content": "<image>\nAnalyze this invoice. Extract vendor name, total amount, and validate arithmetic..."
    },
    {
      "role": "assistant",
      "content": "{\"structured_data\": {...}, \"validation_summary\": {...}}"
    }
  ]
}
```

### Creating Pairs from Your Data

The `prepare_data.py` script converts:
- **Active learning data** (`active_learning.jsonl`) → Instruction pairs
- **Synthetic invoices** (manifest + images + ground truth) → Instruction pairs

## Training Configuration

### LoRA Settings

```yaml
lora:
  enabled: true
  r: 16                    # LoRA rank (higher = more parameters)
  lora_alpha: 32          # Scaling (typically 2x rank)
  target_modules: ["q_proj", "v_proj", "k_proj", "o_proj"]
  lora_dropout: 0.1
```

**Recommendations:**
- Start with `r=16` for faster training
- Increase to `r=32` or `r=64` if you need better quality
- Higher rank = more trainable parameters = better adaptation

### Training Hyperparameters

```yaml
training:
  num_train_epochs: 3
  per_device_train_batch_size: 2
  gradient_accumulation_steps: 4      # Effective batch = 8
  learning_rate: 2.0e-4
  warmup_steps: 100
  fp16: true                          # Use mixed precision
```

**Adjustments:**
- **Out of memory**: Reduce `per_device_train_batch_size` or increase `gradient_accumulation_steps`
- **Slow convergence**: Increase learning rate to `3e-4` or `5e-4`
- **Overfitting**: Reduce epochs or add more data

## Integration with ERNIEKit

### Using Official ERNIEKit

If you have access to ERNIEKit (official PaddlePaddle toolkit):

1. **Install ERNIEKit**
   ```bash
   # Follow ERNIEKit installation guide
   git clone https://github.com/PaddlePaddle/ERNIEKit
   cd ERNIEKit
   pip install -e .
   ```

2. **Adapt Configuration**
   Convert `erniekit_config.yaml` to ERNIEKit's expected format

3. **Run Training**
   ```bash
   erniekit train --config erniekit_config.yaml
   ```

### Using HuggingFace PEFT (Current Implementation)

The provided `train_ernie_lora.py` uses HuggingFace PEFT, which works if:
- ERNIE models are available on HuggingFace
- Models follow standard Transformers architecture

**Current Status:**
- ERNIE models are available on HuggingFace: https://huggingface.co/collections/baidu/ernie-45
- May require custom model loading (see script comments)

## Evaluation

After training, evaluate your fine-tuned model:

```bash
python erniekit_finetuning/evaluate.py \
    --model ./finetuned_ernie \
    --test-data data/test_ernie.jsonl \
    --output results.json
```

**Metrics to track:**
- JSON formatting accuracy
- Field extraction accuracy
- Validation rule compliance
- Arithmetic verification rate

## Integration with Your Service

### Update ERNIE Service

**File:** `app/core/models/ernie_vlm_service.py`

```python
class ErnieVLMService:
    def __init__(self, config: Dict[str, Any]):
        # ... existing code ...
        
        # Load fine-tuned model if available
        fine_tuned_path = config.get("ernie_vl", {}).get("fine_tuned_model_path")
        if fine_tuned_path and os.path.exists(fine_tuned_path):
            from peft import PeftModel
            from transformers import AutoModelForVision2Seq
            
            # Load base model
            base_model = AutoModelForVision2Seq.from_pretrained(
                "baidu/ERNIE-4.5-8B",
                trust_remote_code=True
            )
            
            # Load LoRA adapters
            self.model = PeftModel.from_pretrained(base_model, fine_tuned_path)
            logger.info(f"Loaded fine-tuned ERNIE model from {fine_tuned_path}")
```

### Configuration

**File:** `app/config/settings.py` or environment variables:

```bash
ERNIE_FINETUNED_PATH=./finetuned_ernie
```

## Troubleshooting

### Out of Memory

- Reduce `per_device_train_batch_size` to 1
- Increase `gradient_accumulation_steps` to maintain effective batch size
- Enable `fp16` or `bf16` (mixed precision)
- Use smaller model (ERNIE-4.5-8B instead of 28B)

### Model Not Loading

- Check if ERNIE models are available on HuggingFace
- Verify model name matches HuggingFace repository
- May need custom loading code (see ERNIEKit documentation)

### Poor Performance

- Increase training data (aim for 5K+ instruction pairs)
- Increase LoRA rank (`r=32` or `r=64`)
- Train for more epochs
- Check data quality (instruction pairs correctly formatted)

### Slow Training

- Enable Flash Attention (if supported)
- Use multiple GPUs with `accelerate`
- Reduce logging frequency
- Use gradient checkpointing

## When to Fine-Tune vs Use API

### Fine-Tune When:
- ✅ You need specific output formatting
- ✅ You want to reduce API costs
- ✅ You have domain-specific validation rules
- ✅ You want to demonstrate full customization

### Use API When:
- ✅ You want access to latest models (ERNIE 5)
- ✅ You don't have GPU resources
- ✅ You want "thinking" mode capabilities
- ✅ You need faster iteration (current approach)

## References

- [ERNIEKit GitHub](https://github.com/PaddlePaddle/ERNIEKit)
- [HuggingFace PEFT](https://huggingface.co/docs/peft)
- [LoRA Paper](https://arxiv.org/abs/2106.09685)
- [ERNIE on HuggingFace](https://huggingface.co/collections/baidu/ernie-45)
- [Your ERNIE Integration Guide](../ERNIE_INTEGRATION.md)

## Next Steps

1. **Prepare Data**: Generate instruction pairs from your data
2. **Train Model**: Run fine-tuning with LoRA
3. **Evaluate**: Test on held-out data
4. **Integrate**: Update service to use fine-tuned model
5. **Compare**: A/B test API vs fine-tuned model

