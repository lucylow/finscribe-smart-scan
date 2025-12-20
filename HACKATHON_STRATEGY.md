# Hackathon Strategy: PaddleOCR-VL Customization & ERNIE Fine-Tuning

This document outlines the complete strategy for customizing **PaddleOCR-VL** and fine-tuning **ERNIE models** for the FinScribe Smart Scan hackathon project, specifically targeting the "Best PaddleOCR-VL Fine-Tune" prize.

## Table of Contents

1. [Overview](#overview)
2. [Technology Comparison](#technology-comparison)
3. [Recommended Strategy](#recommended-strategy)
4. [PaddleOCR-VL Customization](#paddleocr-vl-customization)
5. [ERNIE Fine-Tuning](#ernie-fine-tuning)
6. [Implementation Roadmap](#implementation-roadmap)
7. [Integration with Existing System](#integration-with-existing-system)

## Overview

Your FinScribe Smart Scan system uses a two-stage pipeline:
1. **PaddleOCR-VL** (Stage 1): Extracts text and layout from financial documents
2. **ERNIE VLM** (Stage 2): Performs semantic reasoning and validation

For the hackathon, you can enhance both stages through customization and fine-tuning.

## Technology Comparison

| Feature | **PaddleOCR-VL Customization** | **ERNIE Open-Source Model Fine-Tuning** |
| :--- | :--- | :--- |
| **Primary Goal** | Train a specialized OCR pipeline for financial invoices | Adapt a general-purpose reasoning model for financial domain logic |
| **Typical Method** | **Supervised training** of detection & recognition models from scratch or via fine-tuning | **Parameter-Efficient Fine-Tuning (PEFT)**, like LoRA, on pre-trained model using instruction-response pairs |
| **Key Tools** | PaddleOCR training scripts (`tools/train.py`), custom datasets with annotations | **ERNIEKit** (official PaddlePaddle toolkit), Hugging Face's PEFT library, Axolotl |
| **Best For** | **Core Task Accuracy**: Making the model exceptionally good at reading text and understanding layout from *your specific documents* | **Task Intelligence**: Teaching the model financial semantics, validation rules, and structured JSON output |
| **Resource Need** | High-quality labeled data (text bounding boxes and transcripts). Moderate GPU resources for training detection/recognition nets. | Curated dataset of instruction-response pairs. For 28B parameter ERNIE model, significant GPU memory (~80GB) required to load, but PEFT reduces training cost |

## Recommended Strategy

Given the hackathon timeline and the goal of winning the "Best PaddleOCR-VL Fine-Tune" prize:

### 🎯 Primary Focus: Fine-Tune PaddleOCR-VL

This directly addresses the competition category. Use your **synthetic invoice dataset** to train the text detection and recognition models. The goal is to show measurable accuracy improvement on financial documents over the base model.

**Why this approach:**
- ✅ Directly targets the competition prize
- ✅ You already have fine-tuning infrastructure (`finscribe/training/`, `train_finscribe_vl.py`)
- ✅ Synthetic data generation is already set up (`synthetic_invoice_generator/`)
- ✅ LoRA support is implemented for memory efficiency

### 🚀 Enhancement: Use ERNIE-4.5-VL via API (Current Approach)

Instead of fine-tuning ERNIE yourself (which is resource-intensive), you can call its powerful **"Thinking with Images"** capability via its inference API. Your backend already does this:

1. **PaddleOCR-VL** extracts text and layout (Stage 1)
2. **ERNIE VLM** validates and enriches the data (Stage 2)

This leverages ERNIE's superior reasoning without training overhead.

### 🔬 Advanced Option: ERNIEKit Fine-Tuning (If Resources Available)

If you have GPU resources and want to demonstrate full customization, use **ERNIEKit to apply LoRA fine-tuning** to a smaller ERNIE model specifically for formatting the final JSON output.

## PaddleOCR-VL Customization

### Current Implementation

You already have:
- ✅ Fine-tuning infrastructure: `finscribe/training/`
- ✅ Training script: `train_finscribe_vl.py`
- ✅ Dataset preparation: `finscribe/data/`
- ✅ Synthetic data generator: `synthetic_invoice_generator/`
- ✅ Evaluation tools: `finscribe/eval/`

### Three-Step Pipeline (Official PaddleOCR Approach)

The official PaddleOCR guide outlines a three-step pipeline:

#### 1. Train a Text Detection Model

Teach the model to find all text regions in your invoices. Algorithms like `DB` (Differentiable Binarization) with backbones like `MobileNetV3` for efficiency.

**Key Requirements:**
- Labeled dataset with bounding boxes for all text regions
- Ground truth annotations in PaddleOCR format

**Your Synthetic Data Advantage:**
Your `synthetic_invoice_generator` can produce perfect ground truth bounding boxes automatically!

#### 2. Train a Text Recognition Model

Teach the model to accurately transcribe text from those regions. Algorithms like `CRNN` (Convolutional Recurrent Neural Network).

**Key Requirements:**
- Cropped text regions with transcripts
- Character-level annotations

#### 3. Concatenate the Models

Combine your trained detection and recognition models into a single, end-to-end OCR system.

### Implementation Steps

1. **Generate Training Data** (Already Available)
   ```bash
   python synthetic_invoice_generator/generate_dataset.py \
       --num_samples 10000 \
       --output_dir data/training
   ```

2. **Convert to PaddleOCR Format**
   Create a script to convert your synthetic invoice annotations to PaddleOCR's training format:
   - Detection: `image_path\t[{"transcription": "text", "points": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]}]`
   - Recognition: Cropped images with text labels

3. **Train Detection Model**
   ```bash
   # Using PaddleOCR training scripts
   python tools/train.py \
       --config configs/det/det_mv3_db.yml \
       --train_data_path data/training/detection \
       --save_model_path models/detection
   ```

4. **Train Recognition Model**
   ```bash
   python tools/train.py \
       --config configs/rec/rec_mv3_crnn.yml \
       --train_data_path data/training/recognition \
       --save_model_path models/recognition
   ```

5. **Integrate with Your Service**
   Update `app/core/models/paddleocr_vl_service.py` to use your fine-tuned models.

### Alternative: End-to-End Fine-Tuning (Your Current Approach)

Your current approach fine-tunes PaddleOCR-VL-0.9B end-to-end using LoRA, which is more practical for the hackathon:

```bash
python train_finscribe_vl.py \
    --data-dir data/training \
    --output-dir ./finetuned_finscribe_vl \
    --epochs 4 \
    --batch-size 4 \
    --use-lora \
    --lora-r 16 \
    --learning-rate 2e-5
```

**Advantages:**
- ✅ Single training step (faster iteration)
- ✅ LoRA reduces memory requirements
- ✅ Already implemented in your codebase
- ✅ Works with your synthetic data format

## ERNIE Fine-Tuning

### Current Implementation

You already have:
- ✅ ERNIE VLM service: `app/core/models/ernie_vlm_service.py`
- ✅ Support for ERNIE 5, ERNIE 4.5 VL, ERNIE 4.5
- ✅ API integration via vLLM server
- ✅ Active learning logging: `active_learning.jsonl`

### Why Use PEFT (LoRA)

Fine-tuning the entire 28B parameter ERNIE model is prohibitively expensive. **LoRA (Low-Rank Adaptation)** is the standard method:
- Adds tiny, trainable "adapter" layers
- Keeps original knowledge intact
- Minimizes computational cost
- Requires ~80GB GPU memory to load model, but training is efficient

### The Official Tool: ERNIEKit

For the ERNIE series, Baidu provides **ERNIEKit**, a PaddlePaddle-based toolkit designed for:
- Instruction fine-tuning (SFT)
- Alignment training
- LoRA support

### What to Teach It (Data Format)

You need to create a dataset of `(prompt, response)` pairs. For example:

**Prompt:**
```
<image_of_invoice>
Analyze this invoice. Extract the vendor name, total amount, and verify that the subtotal plus tax equals the grand total.
```

**Response:**
```json
{
  "vendor": "ABC Corp",
  "total": 143.00,
  "arithmetic_valid": true,
  "structured_data": {
    "vendor_block": {"name": "ABC Corp", ...},
    "financial_summary": {"grand_total": 143.00, ...}
  }
}
```

### Implementation with ERNIEKit

See `erniekit_finetuning/` directory for complete implementation.

**Key Steps:**

1. **Prepare Instruction Pairs**
   ```python
   from phase2_finetuning.create_instruction_pairs import create_ernie_pairs
   
   pairs = create_ernie_pairs(
       image_path="invoice.png",
       ocr_result={...},
       ground_truth={...}
   )
   ```

2. **Configure ERNIEKit Training**
   ```yaml
   # erniekit_config.yaml
   model_name: "baidu/ERNIE-4.5-8B"  # Use smaller model for fine-tuning
   dataset_path: "ernie_finetune_data.jsonl"
   lora:
     enabled: true
     r: 16
     lora_alpha: 32
   ```

3. **Run Training**
   ```bash
   # Using ERNIEKit (if available)
   erniekit train --config erniekit_config.yaml
   
   # OR using HuggingFace PEFT directly
   python erniekit_finetuning/train_ernie_lora.py \
       --config erniekit_config.yaml
   ```

### Alternative: Use ERNIE API (Current Approach)

Your current implementation uses ERNIE via API, which is more practical:

- ✅ No training overhead
- ✅ Access to latest models (ERNIE 5, ERNIE 4.5 VL)
- ✅ "Thinking" mode for complex reasoning
- ✅ Already integrated in `ErnieVLMService`

**When to Fine-Tune Instead:**
- You need domain-specific output formatting
- You want to reduce API costs
- You have specific validation rules to hard-code
- You want to demonstrate full customization

## Implementation Roadmap

### Phase 1: PaddleOCR-VL Fine-Tuning (Priority) ⭐

**Timeline: 2-3 days**

1. **Day 1: Data Preparation**
   - [ ] Generate 10K+ synthetic invoices
   - [ ] Convert to training format
   - [ ] Split train/val/test (80/10/10)

2. **Day 2: Training**
   - [ ] Run fine-tuning with LoRA
   - [ ] Monitor training metrics
   - [ ] Save checkpoints

3. **Day 3: Evaluation & Integration**
   - [ ] Evaluate on test set
   - [ ] Compare base vs fine-tuned
   - [ ] Integrate fine-tuned model into service
   - [ ] Benchmark performance improvement

**Success Metrics:**
- Field extraction accuracy: >95% (vs ~90% baseline)
- Table structure accuracy (TEDS): >90%
- Numerical validation rate: >98%

### Phase 2: ERNIE Fine-Tuning (Optional)

**Timeline: 1-2 days (if resources available)**

1. **Prepare Instruction Pairs**
   - [ ] Convert active learning data to instruction pairs
   - [ ] Create validation prompts
   - [ ] Format for ERNIEKit

2. **Fine-Tune with LoRA**
   - [ ] Configure ERNIEKit
   - [ ] Train on instruction pairs
   - [ ] Evaluate on test set

3. **Integration**
   - [ ] Update `ErnieVLMService` to use fine-tuned model
   - [ ] A/B test API vs fine-tuned

**Success Metrics:**
- JSON formatting accuracy: >98%
- Validation rule compliance: >95%
- Response latency: <500ms

## Integration with Existing System

### Current Architecture

```
Document Upload
    ↓
PaddleOCR-VL Service (Stage 1: OCR)
    ↓
ERNIE VLM Service (Stage 2: Reasoning)
    ↓
Financial Validator
    ↓
Structured Output
```

### After Fine-Tuning

```
Document Upload
    ↓
Fine-Tuned PaddleOCR-VL Service (Stage 1: Enhanced OCR)
    ↓
ERNIE VLM Service (Stage 2: Reasoning) [or Fine-Tuned ERNIE]
    ↓
Financial Validator
    ↓
Structured Output (Higher Accuracy)
```

### Code Changes Required

#### 1. Update PaddleOCR-VL Service

**File:** `app/core/models/paddleocr_vl_service.py`

```python
class PaddleOCRVLService:
    def __init__(self, config: Dict[str, Any]):
        # ... existing code ...
        
        # Load fine-tuned model if available
        fine_tuned_path = config.get("paddleocr_vl", {}).get("fine_tuned_model_path")
        if fine_tuned_path and os.path.exists(fine_tuned_path):
            self.use_fine_tuned = True
            # Load fine-tuned model
            # (implementation depends on model format)
        else:
            self.use_fine_tuned = False
```

#### 2. Update ERNIE Service (If Fine-Tuning)

**File:** `app/core/models/ernie_vlm_service.py`

```python
class ErnieVLMService:
    def __init__(self, config: Dict[str, Any]):
        # ... existing code ...
        
        # Support for fine-tuned ERNIE model
        fine_tuned_path = config.get("ernie_vl", {}).get("fine_tuned_model_path")
        if fine_tuned_path:
            # Load fine-tuned model with LoRA adapters
            # (implementation depends on ERNIEKit/PEFT format)
```

#### 3. Configuration Updates

**File:** `app/config/settings.py`

```python
"paddleocr_vl": {
    "vllm_server_url": os.getenv("PADDLEOCR_VLLM_URL", "http://localhost:8001/v1"),
    "model_name": "PaddlePaddle/PaddleOCR-VL",
    "fine_tuned_model_path": os.getenv("PADDLEOCR_FINETUNED_PATH", None),  # New
    "timeout": int(os.getenv("PADDLEOCR_TIMEOUT", "30"))
},
"ernie_vl": {
    "vllm_server_url": os.getenv("ERNIE_VLLM_URL", "http://localhost:8002/v1"),
    "model_name": os.getenv("ERNIE_MODEL_NAME", "baidu/ERNIE-5"),
    "fine_tuned_model_path": os.getenv("ERNIE_FINETUNED_PATH", None),  # New
    "timeout": int(os.getenv("ERNIE_TIMEOUT", "60"))
}
```

## Quick Start Commands

### PaddleOCR-VL Fine-Tuning

```bash
# 1. Generate training data
python synthetic_invoice_generator/generate_dataset.py \
    --num_samples 10000 \
    --output_dir data/training

# 2. Build dataset
python finscribe/data/build_dataset.py \
    --data-dir data/training \
    --output data/dataset.jsonl

# 3. Train with LoRA
python train_finscribe_vl.py \
    --data-dir data/training \
    --output-dir ./finetuned_finscribe_vl \
    --epochs 4 \
    --batch-size 4 \
    --use-lora \
    --lora-r 16 \
    --learning-rate 2e-5

# 4. Evaluate
python compare_base_vs_finetuned.py \
    --image data/test_invoice.png \
    --model ./finetuned_finscribe_vl \
    --output comparison.json
```

### ERNIE Fine-Tuning (If Using ERNIEKit)

```bash
# 1. Prepare instruction pairs
python erniekit_finetuning/prepare_data.py \
    --active-learning-file active_learning.jsonl \
    --output ernie_finetune_data.jsonl

# 2. Train with LoRA
python erniekit_finetuning/train_ernie_lora.py \
    --config erniekit_config.yaml \
    --output-dir ./finetuned_ernie

# 3. Evaluate
python erniekit_finetuning/evaluate.py \
    --model ./finetuned_ernie \
    --test-data data/test_ernie.jsonl
```

## Resources & References

### PaddleOCR-VL
- [PaddleOCR Official Docs](https://github.com/PaddlePaddle/PaddleOCR)
- [PaddleOCR-VL HuggingFace](https://huggingface.co/PaddlePaddle/PaddleOCR-VL)
- [Your Fine-Tuning Guide](./FINETUNING_GUIDE.md)

### ERNIE
- [ERNIE Official](https://ernie.baidu.com)
- [ERNIEKit GitHub](https://github.com/PaddlePaddle/ERNIEKit)
- [ERNIE 4.5 Blog](https://yiyan.baidu.com/blog/posts/ernie4.5/)
- [HuggingFace ERNIE Collection](https://huggingface.co/collections/baidu/ernie-45)
- [Your ERNIE Integration Guide](./ERNIE_INTEGRATION.md)

### LoRA & PEFT
- [LoRA Paper](https://arxiv.org/abs/2106.09685)
- [HuggingFace PEFT](https://huggingface.co/docs/peft)

## Next Steps

1. **Immediate**: Focus on PaddleOCR-VL fine-tuning (Phase 1)
2. **If Time Permits**: Implement ERNIEKit fine-tuning (Phase 2)
3. **Documentation**: Update README with fine-tuning results
4. **Demo**: Prepare comparison demo (base vs fine-tuned)

## Questions?

For specific implementation details:
- PaddleOCR-VL: See `FINETUNING_GUIDE.md`
- ERNIE Integration: See `ERNIE_INTEGRATION.md`
- Phase 2 Strategy: See `phase2_finetuning/README.md`

