# FinScribe AI Training Strategy
## PaddleOCR-VL Fine-Tuning Methodology

This document outlines the comprehensive training strategy for fine-tuning PaddleOCR-VL on financial documents, based on the official PaddleOCR-VL training methodology.

## 📊 Strategy Overview

### Core Principles (from PaddleOCR-VL Official Methodology)

1. **Massive Synthetic Dataset**: Build 30M+ samples through synthesis and public sources
2. **Automated Labeling**: Use prompt engineering with base models for auto-labeling
3. **Hard Sample Mining**: Identify weak spots and synthesize challenging examples
4. **Two-Stage Architecture**: Focus fine-tuning on VLM (0.9B), layout model is already excellent
5. **Instruction Fine-Tuning**: Structured output (JSON/Markdown) with instruction-response pairs

## 🛠️ Training Roadmap

### Phase 1: Data Collection & Synthesis

**Goal**: Create a diverse, high-quality dataset of financial documents

#### 1.1 Synthetic Data Generation
- **Volume**: Start with 10K-50K synthetic invoices, receipts, POs
- **Diversity**:
  - Multiple layouts (traditional, modern, international)
  - Various fonts and styles
  - Different currencies (USD, EUR, GBP, JPY, etc.)
  - Multi-language support (English, Spanish, French, etc.)
  - Realistic augmentations (skew, noise, rotation, lighting)

#### 1.2 Data Sources
- **Synthetic**: Use `Faker`, `reportlab`, custom templates
- **Public Datasets**: 
  - CORD (Receipt OCR Dataset)
  - FUNSD (Form Understanding)
  - DocBank (Document Bank)
- **Real Documents**: Collect and manually annotate 500-1000 real documents

#### 1.3 Automated Labeling
- Use base PaddleOCR-VL to extract initial text/layout
- Refine labels using rule-based validation
- Use LLM (GPT-4/Claude) for semantic validation

### Phase 2: Instruction-Based Fine-Tuning

**Goal**: Train model to extract structured data from financial documents

#### 2.1 Instruction-Response Pair Format

```json
{
  "image": "path/to/invoice.png",
  "conversations": [
    {
      "role": "human",
      "content": "<image>\nExtract all fields from this invoice into JSON format."
    },
    {
      "role": "assistant",
      "content": "{\"vendor\": {\"name\": \"...\", \"address\": \"...\"}, \"invoice_number\": \"...\", \"total\": \"...\", \"line_items\": [...]}"
    }
  ]
}
```

#### 2.2 Instruction Templates

1. **Full Document Extraction**:
   - `"Parse this invoice and extract all fields into JSON."`
   - `"Extract all information from this receipt."`

2. **Region-Specific Extraction**:
   - `"Extract the vendor information from this invoice."`
   - `"Extract the line item table from this invoice."`
   - `"Extract the financial summary (subtotal, tax, total) from this invoice."`

3. **Field-Specific Extraction**:
   - `"What is the invoice number?"`
   - `"What is the total amount due?"`
   - `"List all line items with quantities and prices."`

#### 2.3 Data Augmentation

Apply realistic augmentations during training:
- **Geometric**: Rotation (-5° to +5°), skew, perspective
- **Photometric**: Brightness, contrast, noise (Gaussian, salt-and-pepper)
- **Resolution**: Downsampling, upsampling
- **Artifacts**: Blur, compression artifacts

### Phase 3: Hard Sample Mining

**Goal**: Identify and improve on failure cases

#### 3.1 Evaluation Engine
- Run model on validation set
- Identify errors by:
  - **Element Type**: Vendor name, line items, totals, dates
  - **Error Type**: Missing fields, incorrect values, misaligned tables
  - **Confidence**: Low-confidence predictions

#### 3.2 Hard Sample Synthesis
- For each failure pattern, generate 10-50 synthetic variants
- Focus on:
  - Multi-currency tables
  - Complex nested structures
  - Handwritten annotations
  - Poor quality scans
  - Unusual layouts

#### 3.3 Iterative Improvement
- Add hard samples to training set
- Retrain with updated dataset
- Repeat until validation metrics plateau

### Phase 4: Training Configuration

#### 4.1 Base Model
- **Model**: `PaddlePaddle/PaddleOCR-VL` (0.9B parameters)
- **Source**: Hugging Face
- **Architecture**: Vision-Language Model (VLM)

#### 4.2 Training Framework
- **Primary**: ERNIEKit (official PaddleOCR-VL fine-tuning toolkit)
- **Alternative**: HuggingFace Transformers + PEFT (LoRA)

#### 4.3 Hyperparameters

**Critical Parameters** (from PaddleOCR guidance):
- **Learning Rate**: 1e-5 to 5e-5 (start low, adjust based on loss)
- **Batch Size**: Maximum your GPU can handle (typically 4-16)
- **Epochs**: 3-5 (monitor for overfitting)
- **Warmup Steps**: 100-500 (10% of total steps)

**LoRA Configuration** (if using):
- **Rank (r)**: 16-32
- **Alpha**: 32-64 (typically 2x rank)
- **Target Modules**: `q_proj`, `v_proj`, `k_proj`, `o_proj`
- **Dropout**: 0.05-0.1

**Optimization**:
- **Optimizer**: AdamW
- **Weight Decay**: 0.01
- **Scheduler**: Cosine with warmup
- **Mixed Precision**: FP16/BF16 (if supported)

#### 4.4 Loss Function
- **Base**: Cross-entropy for token prediction
- **Weighted Loss**: 
  - Table cell tokens: 2.0x weight
  - Financial fields (amounts, dates): 1.5x weight
  - Regular tokens: 1.0x weight

### Phase 5: Evaluation & Validation

#### 5.1 Metrics

**Field-Level Accuracy**:
- Per-field extraction accuracy (vendor name, invoice number, total, etc.)
- Exact match vs. fuzzy match (for amounts, dates)

**Table Structure Accuracy**:
- TEDS (Tree-Edit-Distance-Based Similarity) score
- Row/column alignment accuracy
- Cell-level accuracy

**Numerical Validation**:
- Mathematical consistency (subtotal + tax - discount = grand_total)
- Currency format validation
- Date format validation

**Overall Metrics**:
- F1 score (field-level)
- Exact match rate (full document)
- Partial match rate (80%+ fields correct)

#### 5.2 Validation Strategy
- **Hold-out Test Set**: 10-20% of data, never used in training
- **Cross-Validation**: 5-fold CV on training set
- **Real-World Testing**: Test on 100+ real documents

### Phase 6: Deployment & Monitoring

#### 6.1 Model Optimization
- **Quantization**: INT8/INT4 quantization for faster inference
- **Pruning**: Remove unnecessary weights
- **ONNX Export**: For production deployment

#### 6.2 Active Learning
- Collect real-world predictions
- Identify errors and edge cases
- Add to training set for next iteration

## 📈 Expected Results

### Training Timeline
- **Small Dataset** (10K samples): 2-4 hours on single GPU
- **Medium Dataset** (50K samples): 8-12 hours
- **Large Dataset** (100K+ samples): 16-24 hours

### Performance Targets
- **Field Extraction Accuracy**: >95% for common fields
- **Table Structure Accuracy**: >90% TEDS score
- **Numerical Validation**: >98% consistency
- **Inference Speed**: <2 seconds per document

## 🔧 Implementation Files

1. **`training/data_synthesis.py`**: Enhanced synthetic data generation
2. **`training/hard_sample_mining.py`**: Hard sample identification and synthesis
3. **`training/instruction_pairs.py`**: Convert data to instruction-response format
4. **`training/erniekit_train.py`**: ERNIEKit training integration
5. **`training/evaluation.py`**: Comprehensive evaluation metrics
6. **`training/config.yaml`**: Training configuration

## 📚 References

- [PaddleOCR-VL GitHub](https://github.com/PaddlePaddle/PaddleOCR)
- [ERNIEKit Documentation](https://github.com/PaddlePaddle/ERNIEKit)
- [PaddleOCR Fine-Tuning Guide](https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.7/doc/doc_en/finetune_en.md)

## 🚀 Quick Start

See `TRAINING_QUICK_START.md` for step-by-step instructions.

