# Quick Start: LLaMA-Factory Integration

## 🚀 Quick Setup (5 minutes)

### 1. Install LLaMA-Factory
```bash
./scripts/setup_llamafactory.sh
```

Or manually:
```bash
git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory
pip install -e ".[torch,metrics]"
```

### 2. Configure Training
Edit `examples/train_lora/finscribe_lora_sft.yaml` and set:
```yaml
model_name_or_path: meta-llama/Meta-Llama-3-8B-Instruct  # or your model
```

### 3. Train
```bash
cd LLaMA-Factory
llamafactory-cli train ../examples/train_lora/finscribe_lora_sft.yaml
```

### 4. Merge & Export
Edit `examples/merge_lora/finscribe_merge.yaml` and run:
```bash
llamafactory-cli export ../examples/merge_lora/finscribe_merge.yaml
```

### 5. Serve Model
```bash
llamafactory-cli api examples/inference/llama_vllm.yaml
```

### 6. Use in Code
```python
from finscribe.llm_client import ask_model_to_validate

ocr_result = {...}  # your OCR JSON
corrected = ask_model_to_validate(ocr_result)
```

## 🎨 Try the Streamlit UI

```bash
streamlit run app/streamlit_llamafactory.py
```

Configure secrets in `~/.streamlit/secrets.toml`:
```toml
OCR_URL = "http://localhost:8002/v1/ocr"
LLAMA_API_URL = "http://localhost:8000/v1/chat/completions"
LLAMA_MODEL = "finscribe-llama"
```

## 🐳 Docker Quick Start

```bash
docker-compose up --build
```

Services available:
- OCR: http://localhost:8002
- LLaMA-Factory: http://localhost:8000
- Postgres: localhost:5432
- MinIO: http://localhost:9000

## 📚 Full Documentation

See [LLAMAFACTORY_INTEGRATION.md](./LLAMAFACTORY_INTEGRATION.md) for detailed documentation.


