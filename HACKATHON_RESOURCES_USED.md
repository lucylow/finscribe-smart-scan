# Hackathon Resources & Repositories Used

This document clearly states which repositories, tutorials, and resources from the hackathon were used and what modifications were made.

---

## 📚 Official Hackathon Resources Used

### 1. PaddleOCR-VL Fine-Tuning Tutorial

**Source**: [PaddleOCR-VL Fine-Tune using ERNIEKit](https://github.com/PaddlePaddle/ERNIE/blob/release/v1.4/docs/paddleocr_vl_sft.md)

**What We Used**:
- Fine-tuning methodology for PaddleOCR-VL
- Instruction-response pair format
- LoRA configuration approach

**What We Modified**:
- ✅ Implemented **completion-only training** (loss masking on prompt tokens)
- ✅ Created **financial domain-specific instruction pairs** (vendor, line items, totals)
- ✅ Built **synthetic invoice generator** for training data (not in original tutorial)
- ✅ Added **hard-sample mining** for iterative improvement
- ✅ Integrated **semantic region extraction** in post-processing

**Our Implementation**:
- `phase2_finetuning/train_finetune_enhanced.py` - Enhanced training script
- `phase2_finetuning/create_instruction_pairs.py` - Instruction pair generator
- `finscribe/training/collate.py` - Completion-only collator

---

### 2. Baidu AI Studio API

**Source**: [Baidu AI Studio](https://aistudio.baidu.com/overview?lang=en)

**Resource Used**:
- 1 million free tokens upon login
- Additional 1 million tokens after profile verification
- 8 compute points per day for running projects

**What We Used**:
- ERNIE API access via `ERNIE_VLLM_URL`
- ERNIE-5 model for semantic reasoning
- ERNIE-4.5-VL for vision-language tasks

**Our Implementation**:
- `app/core/models/ernie_vlm_service.py` - ERNIE service wrapper
- API integration for document validation and enrichment

**API Documentation Reference**:
- [Run ERNIE](https://ai.baidu.com/ai-doc/AISTUDIO/Mmhslv9lf)
- [Run PaddleOCR-VL](https://ai.baidu.com/ai-doc/AISTUDIO/Dmh4onssk)

---

### 3. PaddleOCR-VL Base Model

**Source**: [PaddleOCR-VL on HuggingFace](https://huggingface.co/PaddlePaddle/PaddleOCR-VL)

**What We Used**:
- Base model: `PaddlePaddle/PaddleOCR-VL` (0.9B parameters)
- Model architecture and weights

**What We Modified**:
- ✅ Fine-tuned with LoRA adapters for financial documents
- ✅ Trained on synthetic invoice dataset
- ✅ Specialized for invoice/receipt/statement parsing

**Our Implementation**:
- `finscribe/training/model.py` - Model loading and configuration
- `finscribe/training/lora.py` - LoRA adapter implementation

---

## 🛠️ Open-Source Tools & Libraries

### 4. HuggingFace Transformers & PEFT

**Source**: [HuggingFace PEFT](https://huggingface.co/docs/peft)

**What We Used**:
- PEFT library for LoRA fine-tuning
- Transformers library for model loading
- Datasets library for data handling

**Our Implementation**:
- LoRA configuration in `phase2_finetuning/finetune_config.yaml`
- Model loading in `finscribe/training/model.py`

---

### 5. FastAPI Framework

**Source**: [FastAPI](https://fastapi.tiangolo.com/)

**What We Used**:
- FastAPI for backend API
- OpenAPI/Swagger documentation
- Pydantic for data validation

**Our Implementation**:
- `app/main.py` - FastAPI application
- `app/api/v1/` - API endpoints

---

### 6. React + TypeScript Frontend

**Source**: Standard React ecosystem

**What We Used**:
- React 18+ with TypeScript
- shadcn/ui components
- TanStack Query for state management

**Our Implementation**:
- `src/` - Complete React frontend application
- `src/pages/FinScribe.tsx` - Main application page

---

## 📝 Additional Resources (Not from Hackathon)

### Synthetic Data Generation

**Our Original Work**:
- `synthetic_invoice_generator/` - Complete synthetic invoice generator
- Generates perfectly labeled training data
- Multiple layout variations and augmentations

**Why This Matters**:
- Provides unlimited training data with perfect ground truth
- Enables reproducible experiments
- No annotation errors or inconsistencies

---

### Evaluation & Comparison Tools

**Our Original Work**:
- `compare_base_vs_finetuned_enhanced.py` - Comprehensive comparison tool
- `finscribe/eval/` - Evaluation metrics (field accuracy, TEDS, numeric validation)

**Why This Matters**:
- Demonstrates clear improvements over baseline
- Provides quantitative metrics for hackathon judges
- Shows production-ready evaluation pipeline

---

### Post-Processing Intelligence

**Our Original Work**:
- `app/core/post_processing/intelligence.py` - Semantic region extraction
- `app/core/validation/financial_validator.py` - Business rule validation

**Why This Matters**:
- Converts raw OCR output to structured JSON
- Validates arithmetic relationships
- Flags uncertain extractions for human review

---

## 🔄 Summary of Modifications

### Key Innovations Beyond Tutorials

1. **Completion-Only Training**: 
   - Not explicitly shown in ERNIEKit tutorial
   - Critical for proper fine-tuning
   - Implemented in `finscribe/training/collate.py`

2. **Financial Domain Specialization**:
   - Created domain-specific instruction pairs
   - Built synthetic invoice generator
   - Added business rule validation

3. **Production-Ready Application**:
   - Complete web interface
   - Real-time processing
   - Batch upload support
   - API integration

4. **Comprehensive Evaluation**:
   - Multiple metrics (field accuracy, TEDS, numeric validation)
   - Side-by-side comparison tool
   - Benchmark results

---

## 📊 Repositories & Forks

### Base Repositories (Not Forked)

- **PaddleOCR-VL**: Used as base model, not forked (loaded from HuggingFace)
- **ERNIEKit**: Methodology followed, not forked (used API access instead)
- **FastAPI/React**: Standard frameworks, not forked

### Our Repository Structure

This is an **original project** that:
- ✅ Uses hackathon resources (Baidu AI Studio, PaddleOCR-VL model)
- ✅ Follows hackathon tutorials (ERNIEKit fine-tuning methodology)
- ✅ Extends beyond tutorials (completion-only training, synthetic data, evaluation)
- ✅ Creates production-ready application

---

## ✅ Compliance with Hackathon Requirements

### Required Checklist

- [x] **Clear statement of repos used**: This document
- [x] **What was modified**: Detailed above
- [x] **Fine-tuning code**: `phase2_finetuning/` directory
- [x] **Configuration files**: `finetune_config.yaml`
- [x] **Data generation scripts**: `synthetic_invoice_generator/`
- [x] **Demo application**: Complete web interface
- [x] **Instructions to run**: README.md and HACKATHON_SUBMISSION.md

---

## 🔗 Links to Original Resources

1. **PaddleOCR-VL Fine-Tune Tutorial**: 
   - GitHub: https://github.com/PaddlePaddle/ERNIE/blob/release/v1.4/docs/paddleocr_vl_sft.md
   - Google Colab: https://colab.research.google.com/drive/1yjbH1zbvBlyUq1wz0pohPaWKHO6szAXb?usp=sharing

2. **Baidu AI Studio**:
   - Registration: https://aistudio.baidu.com/overview?lang=en
   - API Docs: https://ai.baidu.com/ai-doc/AISTUDIO/Mmhslv9lf

3. **PaddleOCR-VL Model**:
   - HuggingFace: https://huggingface.co/PaddlePaddle/PaddleOCR-VL

4. **ERNIE Models**:
   - HuggingFace Collection: https://huggingface.co/collections/baidu/ernie-45

---

## 📝 License & Attribution

- **PaddleOCR-VL**: Apache 2.0 License
- **ERNIE Models**: Baidu AI Studio Terms of Service
- **Our Code**: MIT License (see LICENSE file)

All hackathon resources are properly attributed and used in compliance with their respective licenses.

---

**Last Updated**: 2024-12-20

