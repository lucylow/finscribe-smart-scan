# Unsloth Integration - Quick Start Guide

This is a quick reference guide for getting started with Unsloth in FinScribe.

## 🚀 5-Minute Setup

### 1. Install Unsloth (GPU Required)

```bash
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install transformers datasets accelerate trl bitsandbytes
```

### 2. Test with Demo Data

```bash
# Demo datasets are already in data/
ls data/unsloth_*.jsonl

# Train a quick model (uses demo data)
./scripts/train_unsloth.sh
```

### 3. Use Inference API

```python
from app.core.models.unsloth_service import get_unsloth_service

service = get_unsloth_service()
result = service.infer("Vendor: TechCorp\nInvoice: INV-001...")
print(result)
```

Or via HTTP:
```bash
curl -X POST http://localhost:8000/api/v1/unsloth/infer \
  -H "Content-Type: application/json" \
  -d '{"ocr_text": "Vendor: TechCorp\nInvoice: INV-001..."}'
```

## 📊 Pipeline Flow

```
Document → PaddleOCR → OCR Text → Unsloth → JSON → Validation
```

## 🔧 Key Files

- **Training**: `./scripts/train_unsloth.sh`
- **Service**: `app/core/models/unsloth_service.py`
- **API**: `app/api/v1/unsloth.py`
- **UI**: `streamlit run streamlit_unsloth/app.py`
- **Docs**: `UNSLOTH_INTEGRATION.md`

## 🐳 Docker Quick Start

```bash
# Start Unsloth API service (GPU required)
docker-compose --profile unsloth up unsloth_api

# Start OCR service
docker-compose --profile ocr up ocr_service

# Start both
docker-compose --profile unsloth --profile ocr up
```

## 📝 Active Learning Workflow

1. **Run Streamlit UI**:
   ```bash
   streamlit run streamlit_unsloth/app.py
   ```

2. **Collect Corrections**:
   - Upload documents
   - Run OCR → Unsloth
   - Correct JSON outputs
   - Save to `data/active_learning.jsonl`

3. **Retrain**:
   ```bash
   cat data/active_learning.jsonl >> data/unsloth_train.jsonl
   ./scripts/train_unsloth.sh
   ```

## ⚙️ Configuration

Set environment variables for training:
```bash
export MODEL_NAME="unsloth/Mistral-7B-Instruct-v0.2-bnb-4bit"
export OUTPUT_DIR="./models/unsloth-finscribe"
export NUM_EPOCHS=3
export USE_LORA=true
```

## 🎓 Next Steps

1. **Replace demo data** with your real invoice datasets
2. **Fine-tune prompts** for better extraction
3. **Collect corrections** via Streamlit UI
4. **Retrain periodically** to improve accuracy

## 📚 Full Documentation

- See `UNSLOTH_INTEGRATION.md` for comprehensive guide
- See `unsloth/README.md` for detailed training instructions
- See `data/README.md` for dataset format

## 🔗 Resources

- [Unsloth GitHub](https://github.com/unslothai/unsloth)
- [Unsloth Docs](https://docs.unsloth.ai/)
- [Unsloth HF Models](https://huggingface.co/unsloth)


