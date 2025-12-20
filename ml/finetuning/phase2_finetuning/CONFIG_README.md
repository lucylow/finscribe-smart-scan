# Hyperparameter Configuration Guide

This directory contains comprehensive hyperparameter configuration files and tools for fine-tuning PaddleOCR-VL for financial document analysis.

## 📁 Files Overview

### Core Configuration
- **`finetune_config.yaml`** - Enhanced baseline configuration with detailed documentation
  - Comprehensive comments explaining each hyperparameter
  - Recommended values based on best practices
  - Experiment tracking section for documenting results

### Documentation
- **`HYPERPARAMETER_TUNING_GUIDE.md`** - Complete guide to hyperparameter tuning
  - Systematic experimentation strategy
  - Detailed explanations of each hyperparameter
  - Example experiment configurations
  - Monitoring and evaluation guidance

### Automation Tools
- **`run_experiments.py`** - Automated experiment runner
  - Runs multiple experiments systematically
  - Creates experiment configs from baseline
  - Tracks results and summaries

- **`experiments_example.yaml`** - Example experiment definitions
  - Pre-configured experiments for common hyperparameter sweeps
  - Learning rate, batch size, warmup, weight decay experiments
  - Ready to use or customize

## 🚀 Quick Start

### 1. Review Baseline Configuration

```bash
# Open and review the baseline config
cat finetune_config.yaml
```

Key hyperparameters in the baseline:
- Learning Rate: `2e-5` (middle of recommended range)
- Batch Size: `8` (good balance)
- Max Sequence Length: `2048` (accommodates full JSON output)
- Epochs: `5` (with early stopping)

### 2. Run Baseline Training

```bash
# Train with baseline configuration
python train_finetune.py --config finetune_config.yaml
```

### 3. Run Systematic Experiments

```bash
# Create your experiments file based on experiments_example.yaml
cp experiments_example.yaml experiments.yaml

# Edit experiments.yaml to define your experiments
# Then run all experiments:
python run_experiments.py --baseline-config finetune_config.yaml --experiments experiments.yaml

# Or run a single experiment:
python run_experiments.py --baseline-config finetune_config.yaml --experiments experiments.yaml --name lr_1e5

# Dry run (just create configs, don't train):
python run_experiments.py --baseline-config finetune_config.yaml --experiments experiments.yaml --dry-run
```

## 📊 Hyperparameter Quick Reference

| Hyperparameter | Baseline | Range | Most Critical? |
|---------------|----------|-------|----------------|
| **Learning Rate** | `2e-5` | `1e-5` to `5e-5` | ✅ YES |
| **Batch Size** | `8` | `4` to `16` | ✅ YES |
| **Max Sequence Length** | `2048` | `2048+` | ✅ YES |
| **Epochs** | `5` | `3` to `10` | ⚠️ Moderate |
| **Warmup Ratio** | `0.1` | `0.05` to `0.1` | ⚠️ Moderate |
| **Weight Decay** | `0.01` | `0.01` to `0.1` | ⚠️ Moderate |

## 🔬 Recommended Experiment Sequence

1. **Phase 1: Establish Baseline**
   - Run `finetune_config.yaml`
   - Document metrics (loss, accuracy, TEDS)

2. **Phase 2: Learning Rate Sweep**
   - Test: `1e-5`, `2e-5`, `5e-5`
   - Choose highest stable LR with best metrics

3. **Phase 3: Batch Size Optimization**
   - Test: `4`, `8`, `16` (with proportional LR adjustment!)
   - Choose largest that fits in GPU memory

4. **Phase 4: Fine-Tuning** (if time permits)
   - Warmup ratio: `0.05`, `0.1`, `0.15`
   - Weight decay: `0.01`, `0.05`, `0.1`

5. **Phase 5: Combined Optimal**
   - Combine best individual parameters
   - Final validation

## ⚙️ Key Configuration Sections

### Training Hyperparameters
```yaml
training:
  learning_rate: 2.0e-5        # MOST CRITICAL - adjust carefully
  per_device_train_batch_size: 8
  gradient_accumulation_steps: 2
  num_train_epochs: 5
  max_sequence_length: 2048    # CRITICAL - must fit your JSON output
  warmup_ratio: 0.1
  weight_decay: 0.01
```

### LoRA Configuration
```yaml
lora:
  enabled: true
  r: 16                        # LoRA rank (higher = more capacity)
  lora_alpha: 32              # Typically 2 * r
  target_modules: ["q_proj", "v_proj", "k_proj", "o_proj"]
```

### Early Stopping
```yaml
early_stopping:
  enabled: true
  patience: 3                  # Stop after 3 evals without improvement
  metric: "eval_loss"
```

## 📈 Monitoring Metrics

Track these metrics during training:
1. **Validation Loss** - Primary metric for model selection
2. **Field Extraction Accuracy** - Per-region accuracy for 5 semantic regions
3. **TEDS Score** - Table structure accuracy (target: > 0.90)
4. **Training Time** - Practical consideration
5. **GPU Memory Usage** - Ensure you're maximizing utilization

## 💡 Pro Tips

1. **Always adjust LR proportionally with batch size:**
   - Batch 4 → LR 1e-5
   - Batch 8 → LR 2e-5
   - Batch 16 → LR 4e-5

2. **Use early stopping:**
   - Prevents overfitting
   - Saves time
   - Automatically selects best checkpoint

3. **Monitor TensorBoard:**
   ```bash
   tensorboard --logdir ./finetuned_paddleocr_invoice_model/runs
   ```

4. **Document everything:**
   - Update `experiment.results` section after each run
   - Keep notes on what worked/didn't work
   - Essential for hackathon submission!

## 🎯 For Your Hackathon Submission

Make sure to document:
- ✅ Baseline configuration and results
- ✅ Systematic experiments run (with configs)
- ✅ Comparison of results (loss, accuracy, TEDS)
- ✅ Justification for final hyperparameter choices
- ✅ Any interesting findings or observations

## 📚 Additional Resources

- See `HYPERPARAMETER_TUNING_GUIDE.md` for detailed explanations
- See `experiments_example.yaml` for example experiment definitions
- See `train_finetune.py` for training script implementation

---

**Remember:** Systematic, one-parameter-at-a-time experimentation is the key to success!

