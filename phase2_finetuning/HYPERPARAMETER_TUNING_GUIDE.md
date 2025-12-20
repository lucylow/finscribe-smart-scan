# Hyperparameter Tuning Guide for PaddleOCR-VL Fine-Tuning

This guide provides a systematic approach to tuning hyperparameters for fine-tuning PaddleOCR-VL-0.9B on financial document analysis.

## 📋 Table of Contents
1. [Quick Start](#quick-start)
2. [Baseline Configuration](#baseline-configuration)
3. [Systematic Experimentation Strategy](#systematic-experimentation-strategy)
4. [Key Hyperparameters Explained](#key-hyperparameters-explained)
5. [Example Experiment Configurations](#example-experiment-configurations)
6. [Monitoring & Evaluation](#monitoring--evaluation)

---

## 🚀 Quick Start

1. **Start with the baseline** (`finetune_config.yaml`)
   ```bash
   python train_finetune.py --config finetune_config.yaml
   ```

2. **Establish baseline metrics**
   - Note: validation loss, field extraction accuracy, TEDS score
   - Training time and GPU memory usage

3. **Run focused experiments** (change ONE parameter at a time)
   - See [Example Experiment Configurations](#example-experiment-configurations)

---

## 📊 Baseline Configuration

The baseline configuration (`finetune_config.yaml`) uses conservative values from the recommended ranges:

| Hyperparameter | Baseline Value | Rationale |
|---------------|----------------|-----------|
| Learning Rate | `2e-5` | Middle of recommended range (1e-5 to 5e-5) |
| Batch Size | `8` | Good balance for most GPUs |
| Epochs | `5` | With early stopping, sufficient for most cases |
| Warmup Ratio | `0.1` | 10% of training steps (standard practice) |
| Weight Decay | `0.01` | Moderate regularization |
| Max Sequence Length | `2048` | Accommodates full JSON output |

**Expected Baseline Performance:**
- Training should be stable (no loss spikes or NaN)
- Validation loss should decrease smoothly
- Field extraction accuracy > 85%
- TEDS score > 0.90

---

## 🔬 Systematic Experimentation Strategy

### Phase 1: Establish Strong Baseline
✅ Run baseline configuration
✅ Document metrics (loss, accuracy, time, memory)
✅ Verify training stability

### Phase 2: Learning Rate Ablation
Test learning rates: `1e-5`, `2e-5`, `5e-5`

**Hypothesis:** Lower LR = more stable but slower. Higher LR = faster but risk of instability.

**What to monitor:**
- Training loss curve (should be smooth)
- Validation loss (should decrease steadily)
- Training time per epoch

**Decision criteria:**
- Choose highest LR that remains stable
- If all are stable, choose one with best validation metrics

### Phase 3: Batch Size Optimization
Test batch sizes: `4`, `8`, `16` (adjust LR proportionally!)

**IMPORTANT:** When changing batch size, adjust learning rate proportionally:
- If batch size doubles (8 → 16), double the LR (2e-5 → 4e-5)
- If batch size halves (8 → 4), halve the LR (2e-5 → 1e-5)

**What to monitor:**
- GPU memory usage (should not exceed available VRAM)
- Training stability (gradient variance)
- Final validation metrics

### Phase 4: Secondary Hyperparameters
Once optimal LR and batch size are found:
- Warmup ratio: `0.05`, `0.1`, `0.15`
- Weight decay: `0.01`, `0.05`, `0.1`
- Epochs: Increase if validation loss still decreasing

---

## 📚 Key Hyperparameters Explained

### 1. Learning Rate (`training.learning_rate`)
**Most Critical Parameter**

- **Range:** 1e-5 to 5e-5
- **Too High:** Loss spikes, NaN, training instability
- **Too Low:** Very slow convergence, may not reach optimum
- **Tuning Strategy:** Start at 2e-5, if stable try 5e-5, if unstable try 1e-5

### 2. Batch Size (`training.per_device_train_batch_size`)
**Affects Gradient Stability and Memory**

- **Range:** 4 to 16 (depends on GPU memory)
- **Larger Batch:** More stable gradients, faster training, more memory
- **Smaller Batch:** More gradient noise (sometimes helps generalization), less memory
- **Proportionality:** Always adjust LR proportionally with batch size changes

**Effective Batch Size Formula:**
```
effective_batch = per_device_batch_size × gradient_accumulation_steps × num_gpus
```

### 3. Gradient Accumulation Steps
**Simulates Larger Batch Size**

- Use when you want larger effective batch but are GPU memory constrained
- Example: Want effective batch=16, can only fit 4 in memory → set `gradient_accumulation_steps=4`

### 4. Number of Epochs (`training.num_train_epochs`)
**Complete Passes Through Dataset**

- **Range:** 3 to 10
- **With Early Stopping:** Can set higher (e.g., 10), early stopping will stop if no improvement
- **Monitor:** Validation loss plateau or increase indicates overfitting

### 5. Warmup Ratio (`training.warmup_ratio`)
**Gradual LR Increase at Start**

- **Range:** 0.05 to 0.1
- **Purpose:** Prevents instability in early training phase
- **Typical:** 5-10% of total training steps is sufficient

### 6. Weight Decay (`training.weight_decay`)
**Regularization Against Overfitting**

- **Range:** 0.01 to 0.1
- **Higher Value:** More regularization, better generalization, but may underfit
- **Lower Value:** Less regularization, may overfit to training data

### 7. Max Sequence Length (`training.max_sequence_length`)
**Critical for Your Task!**

- **Recommended:** 2048 or higher
- **Must be:** Long enough to accommodate full JSON output for 5 semantic regions
- **Test:** Check your longest expected JSON output, ensure it fits within this limit
- **Impact:** Too short = truncated outputs, too long = wasted computation

---

## 🔬 Example Experiment Configurations

### Experiment 1: Learning Rate Sweep

Create `experiments/exp1_lr_1e5.yaml`:
```yaml
# Copy from finetune_config.yaml and change:
training:
  learning_rate: 1.0e-5  # Lower end of range

experiment:
  name: "lr_1e5"
  description: "Learning rate = 1e-5 (lower end)"
  hyperparameters_under_test: ["learning_rate"]
```

Create `experiments/exp1_lr_5e5.yaml`:
```yaml
# Copy from finetune_config.yaml and change:
training:
  learning_rate: 5.0e-5  # Upper end of range

experiment:
  name: "lr_5e5"
  description: "Learning rate = 5e-5 (upper end)"
  hyperparameters_under_test: ["learning_rate"]
```

**Run all three (1e-5, 2e-5, 5e-5) and compare:**
- Training stability (no loss spikes)
- Final validation loss
- Training time
- Field extraction accuracy

---

### Experiment 2: Batch Size with Proportional LR

Create `experiments/exp2_batch4.yaml`:
```yaml
# Copy from finetune_config.yaml and change:
training:
  per_device_train_batch_size: 4
  gradient_accumulation_steps: 4  # Keep effective batch = 16
  learning_rate: 1.0e-5  # HALVED from 2e-5 (batch halved from 8)

experiment:
  name: "batch4_lr1e5"
  description: "Batch size = 4, LR = 1e-5 (proportional adjustment)"
```

Create `experiments/exp2_batch16.yaml`:
```yaml
# Copy from finetune_config.yaml and change:
training:
  per_device_train_batch_size: 16
  gradient_accumulation_steps: 1  # No accumulation needed
  learning_rate: 4.0e-5  # DOUBLED from 2e-5 (batch doubled from 8)

experiment:
  name: "batch16_lr4e5"
  description: "Batch size = 16, LR = 4e-5 (proportional adjustment)"
```

**Compare:**
- GPU memory usage
- Training stability
- Final metrics
- Training speed

---

### Experiment 3: Warmup Ratio

Create `experiments/exp3_warmup005.yaml`:
```yaml
# Copy from finetune_config.yaml and change:
training:
  warmup_ratio: 0.05  # Shorter warmup

experiment:
  name: "warmup_0.05"
  description: "Warmup ratio = 0.05 (5% of steps)"
```

Create `experiments/exp3_warmup015.yaml`:
```yaml
# Copy from finetune_config.yaml and change:
training:
  warmup_ratio: 0.15  # Longer warmup

experiment:
  name: "warmup_0.15"
  description: "Warmup ratio = 0.15 (15% of steps)"
```

---

### Experiment 4: Weight Decay

Create `experiments/exp4_wd005.yaml`:
```yaml
# Copy from finetune_config.yaml and change:
training:
  weight_decay: 0.05  # Higher regularization

experiment:
  name: "weight_decay_0.05"
  description: "Weight decay = 0.05 (higher regularization)"
```

---

## 📈 Monitoring & Evaluation

### Key Metrics to Track

1. **Training Loss**
   - Should decrease smoothly
   - Watch for spikes (indicates LR too high)
   - Plateau may indicate convergence

2. **Validation Loss**
   - Primary metric for model selection
   - Should track training loss (gap indicates overfitting)
   - Use for early stopping

3. **Field Extraction Accuracy**
   - Per-region accuracy for 5 semantic regions
   - Target: > 95% for vendor/client blocks, > 90% for tables

4. **TEDS Score (Table Structure Accuracy)**
   - Critical for line item table parsing
   - Target: > 0.90

5. **Numerical Validation**
   - Mathematical consistency checks
   - E.g., subtotal + tax - discount = grand_total

### Using TensorBoard

```bash
# View training logs
tensorboard --logdir ./finetuned_paddleocr_invoice_model/runs
```

**What to look for:**
- Smooth loss curves (no spikes)
- Validation loss should decrease and plateau
- Compare different experiment runs side-by-side

### Early Stopping

Configured in `finetune_config.yaml`:
- **Patience:** 3 evaluations without improvement
- **Metric:** `eval_loss`
- **Benefit:** Prevents overfitting, saves time

---

## ✅ Experiment Checklist

Before starting each experiment:

- [ ] Copy baseline config to new experiment file
- [ ] Update `experiment.name` and `experiment.description`
- [ ] Change ONLY the hyperparameter(s) under test
- [ ] Update `run_name` for easy identification in logs
- [ ] Ensure GPU memory is sufficient for batch size
- [ ] Note start time for training duration tracking

After each experiment:

- [ ] Record final validation loss
- [ ] Record field extraction accuracy (per region)
- [ ] Record TEDS score
- [ ] Record training time
- [ ] Record peak GPU memory usage
- [ ] Update `experiment.results` section in config
- [ ] Save best checkpoint path
- [ ] Document any anomalies or observations

---

## 🎯 Decision Making

### Choosing Best Configuration

Compare experiments on:
1. **Validation Loss** (primary - lower is better)
2. **Field Extraction Accuracy** (task-specific - higher is better)
3. **TEDS Score** (task-specific - higher is better)
4. **Training Stability** (no spikes/NaN - binary)
5. **Training Time** (practical consideration - lower is better)

**Best Configuration:**
- Lowest validation loss
- Highest task-specific metrics
- Stable training (no spikes)
- Reasonable training time

### When to Stop Tuning

- ✅ Validation metrics have plateaued across multiple experiments
- ✅ Consistent improvement is no longer observed
- ✅ Training time exceeds practical limits
- ✅ Task-specific metrics meet your requirements

---

## 📝 Example Experiment Log

```yaml
experiments:
  - name: "baseline_v1"
    config_file: "finetune_config.yaml"
    results:
      final_eval_loss: 0.234
      field_extraction_accuracy: 0.92
      teds_score: 0.91
      training_time_hours: 4.5
      notes: "Stable training, good starting point"
  
  - name: "lr_5e5"
    config_file: "experiments/exp1_lr_5e5.yaml"
    results:
      final_eval_loss: 0.198  # Better!
      field_extraction_accuracy: 0.94  # Better!
      teds_score: 0.93  # Better!
      training_time_hours: 3.8  # Faster!
      notes: "Slightly more unstable but better final metrics"
  
  - name: "batch16_lr4e5"
    config_file: "experiments/exp2_batch16_lr4e5.yaml"
    results:
      final_eval_loss: NaN  # Unstable!
      field_extraction_accuracy: null
      teds_score: null
      training_time_hours: 2.1
      notes: "Loss exploded at step 500, LR too high for this batch size"
```

---

## 🚨 Common Issues & Solutions

### Issue: Loss Explodes (NaN values)
**Solution:** Reduce learning rate by 2-5x

### Issue: Loss Decreases Very Slowly
**Solution:** Increase learning rate (but monitor carefully for instability)

### Issue: GPU Out of Memory
**Solution:** 
- Reduce batch size
- Increase gradient accumulation steps (to maintain effective batch size)
- Enable gradient checkpointing (if supported)

### Issue: Overfitting (large gap between train/val loss)
**Solution:**
- Increase weight decay
- Add more data augmentation
- Reduce model capacity (lower LoRA rank)

### Issue: Underfitting (both train and val loss are high)
**Solution:**
- Increase model capacity (higher LoRA rank)
- Train for more epochs
- Check data quality

---

## 📚 References

- [HuggingFace Transformers Training Docs](https://huggingface.co/docs/transformers/training)
- [LoRA Paper](https://arxiv.org/abs/2106.09685)
- [PaddleOCR-VL Documentation](https://github.com/PaddlePaddle/PaddleOCR)

---

**Remember:** Systematic, one-parameter-at-a-time experimentation is key to finding optimal hyperparameters. Document everything for your hackathon submission!

