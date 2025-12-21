# LLaMA-Factory Integration Guide for FinScribe

This guide explains how to integrate LLaMA-Factory into your FinScribe pipeline for validating and correcting OCR-extracted invoice JSON.

## Quick Start

### 1. Install LLaMA-Factory

```bash
git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory
pip install -e ".[torch,metrics]"
llamafactory-cli version  # verify installation
```

### 2. Prepare Your Dataset

The dataset file `data/finscribe_unsloth.jsonl` contains example invoice validation pairs in Alpaca format. Register it in LLaMA-Factory's `data/dataset_info.json`:

```json
{
  "finscribe_unsloth": {
    "file_name": "finscribe_unsloth.jsonl",
    "format": "jsonl",
    "description": "FinScribe OCR -> validation/correction pairs for invoice JSON"
  }
}
```

### 3. Train LoRA Adapter

Edit `examples/train_lora/finscribe_lora_sft.yaml` to set your `model_name_or_path`, then run:

```bash
llamafactory-cli train examples/train_lora/finscribe_lora_sft.yaml
```

### 4. Merge LoRA to Full Model

Edit `examples/merge_lora/finscribe_merge.yaml` and run:

```bash
llamafactory-cli export examples/merge_lora/finscribe_merge.yaml
```

### 5. Serve Model via API

Start the LLaMA-Factory API server:

```bash
llamafactory-cli api examples/inference/llama_vllm.yaml
```

Or use the web UI:

```bash
llamafactory-cli webui
```

### 6. Integrate with FinScribe

Use the `finscribe.llm_client` module to call the API:

```python
from finscribe.llm_client import ask_model_to_validate

ocr_result = {...}  # your OCR -> structured JSON
corrected = ask_model_to_validate(ocr_result)

if corrected['validation']['arithmetic_valid'] is False:
    # route to human review
    pass
```

## Streamlit UI

Run the interactive UI for testing:

```bash
streamlit run app/streamlit_llamafactory.py
```

Configure secrets in `~/.streamlit/secrets.toml`:

```toml
OCR_URL = "http://localhost:8002/v1/ocr"
LLAMA_API_URL = "http://localhost:8000/v1/chat/completions"
LLAMA_API_KEY = "optional_api_key"
LLAMA_MODEL = "finscribe-llama"
ACTIVE_LEARN_FILE = "data/active_learning_queue.jsonl"
```

## Docker Deployment

Build and run the full stack:

```bash
docker-compose up --build
```

Services:
- **OCR Service**: Port 8002 (PaddleOCR)
- **LLaMA-Factory**: Port 8000 (WebUI/API)
- **Postgres**: Port 5432
- **MinIO**: Ports 9000, 9001

## Unsloth Training Alternative

For faster training with Unsloth:

```bash
./scripts/train_unsloth.sh [model_name] [train_file] [output_dir]
```

## Colab Experiment

See `notebooks/finscribe_llamafactory_micro_experiment.ipynb` for a quick Colab-based micro experiment with 10 synthetic pairs.

## File Structure

```
.
├── app/
│   └── streamlit_llamafactory.py    # Streamlit UI
├── data/
│   ├── finscribe_unsloth.jsonl      # Training dataset
│   └── dataset_info.json            # Dataset registration
├── examples/
│   ├── train_lora/
│   │   └── finscribe_lora_sft.yaml  # SFT config
│   └── merge_lora/
│       └── finscribe_merge.yaml     # Merge config
├── finscribe/
│   └── llm_client.py                # API client
├── scripts/
│   └── train_unsloth.sh             # Unsloth training script
├── docker-compose.yml                # Full stack
├── llamafactory-docker/
│   └── Dockerfile                    # LLaMA-Factory container
└── ocr_service/
    ├── Dockerfile                    # OCR service container
    └── ocr_api.py                    # OCR FastAPI service
```

## References

- [LLaMA-Factory GitHub](https://github.com/hiyouga/LLaMA-Factory)
- [LLaMA-Factory Docs](https://llamafactory.readthedocs.io/)
- [Installation Guide](https://llamafactory.readthedocs.io/en/latest/)
- [SFT Training Guide](https://llamafactory.readthedocs.io/en/latest/)
- [Dataset Format](https://llamafactory.readthedocs.io/en/latest/)

## Notes & Caveats

1. **Model Licensing**: Ensure your base model is licensed for your use case
2. **GPU Requirements**: Training requires GPU; inference is faster on GPU
3. **JSON Output**: Models may occasionally produce extra text; use regex extraction and temperature=0 for more deterministic output
4. **Security**: Add authentication for production deployments
5. **Active Learning**: Accepted corrections from the Streamlit UI are saved to `data/active_learning_queue.jsonl` for periodic retraining


