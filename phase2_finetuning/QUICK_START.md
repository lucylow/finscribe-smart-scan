# Phase 2 Quick Start Guide

## Prerequisites

1. ✅ Phase 1 data generation complete (synthetic invoices)
2. ✅ Python 3.8+ installed
3. ✅ GPU with 16GB+ VRAM (recommended)

## Step-by-Step Guide

### Step 1: Install Dependencies

```bash
cd phase2_finetuning
pip install -r requirements.txt
```

### Step 2: Generate Instruction Pairs

Convert your Phase 1 data to instruction-response pairs:

```bash
python create_instruction_pairs.py \
    --manifest ../synthetic_invoice_generator/output/training_manifest.json \
    --output paddleocr_finetune_data.jsonl
```

**Expected output**: `paddleocr_finetune_data.jsonl` with ~4-5 instruction pairs per invoice.

### Step 3: Review Configuration

Edit `finetune_config.yaml`:

- ✅ Verify `dataset_path` points to your JSONL file
- ✅ Adjust `model_name_or_path` if using custom model
- ✅ Set `per_device_train_batch_size` based on GPU memory
- ✅ Configure LoRA parameters (r=16, alpha=32 is a good starting point)

### Step 4: Start Training

```bash
python train_finetune.py --config finetune_config.yaml
```

**Note**: You may need to adapt `train_finetune.py` based on PaddleOCR-VL's actual API.

### Step 5: Monitor Training

- Check TensorBoard logs: `tensorboard --logdir <output_dir>/runs`
- Monitor loss in console output
- Checkpoints saved in `output_dir` (default: `./finetuned_paddleocr_invoice_model`)

### Step 6: Evaluate

After training, evaluate on test set:

```python
from evaluation_metrics import evaluate_dataset

# Load your test predictions and ground truth
predictions = [...]  # List of JSON response strings
ground_truths = [...]  # List of metadata dictionaries

results = evaluate_dataset(predictions, ground_truths)
print(results)
```

## Common Issues & Solutions

### Issue: Out of Memory

**Solution**:
- Reduce `per_device_train_batch_size` to 2 or 1
- Increase `gradient_accumulation_steps` to maintain batch size
- Enable `fp16: true` in config

### Issue: Files Not Found

**Solution**:
- Verify paths in config are absolute or relative to script location
- Check that Phase 1 data generation completed successfully
- Ensure image files exist and are readable

### Issue: Import Errors

**Solution**:
- Install all dependencies: `pip install -r requirements.txt`
- If using PaddleOCR-VL directly, install PaddlePaddle: `pip install paddlepaddle`
- Check Python version: `python --version` (should be 3.8+)

### Issue: Model Not Loading

**Solution**:
- Verify `model_name_or_path` in config is correct
- Check internet connection (if downloading from HuggingFace)
- If using local model, ensure path is correct

## Expected Training Time

| Dataset Size | Training Time (single GPU) |
|-------------|---------------------------|
| 1,000 invoices | 1-2 hours |
| 5,000 invoices | 4-6 hours |
| 10,000 invoices | 8-12 hours |

*Times assume batch size 4, 5 epochs, on NVIDIA GPU with 16GB+ VRAM*

## Next Steps After Training

1. ✅ Evaluate on held-out test set
2. ✅ Check region-specific accuracies
3. ✅ Review numerical validation errors
4. ✅ Fine-tune hyperparameters if needed
5. ✅ Deploy model for inference
6. ✅ Monitor real-world performance

## Getting Help

- Check `README.md` for detailed documentation
- Review `example_usage.py` for code examples
- Inspect `evaluation_metrics.py` for evaluation details
- Review configuration in `finetune_config.yaml`

