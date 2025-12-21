# Inference Guide: Using FinScribe for Document Processing

This guide explains how to use the fine-tuned FinScribe model for inference on financial documents.

## Quick Start

### Using the API (Recommended)

The easiest way to use FinScribe is through the REST API:

```bash
# Start the backend server
docker-compose up backend

# Or locally:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Upload and analyze a document
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -F "file=@invoice.pdf" \
  -F "mode=async"

# Response:
# {"job_id": "job_abc123", "status": "received"}

# Check job status
curl "http://localhost:8000/api/v1/jobs/job_abc123"

# Get results when complete
curl "http://localhost:8000/api/v1/results/{result_id}"
```

### Using Python SDK

```python
import requests

# Upload document
with open("invoice.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(
        "http://localhost:8000/api/v1/analyze",
        files=files,
        data={"mode": "async"}
    )
    job_id = response.json()["job_id"]

# Poll for results
import time
while True:
    status_response = requests.get(f"http://localhost:8000/api/v1/jobs/{job_id}")
    status = status_response.json()["status"]
    if status == "completed":
        result_id = status_response.json()["result_id"]
        break
    elif status == "failed":
        raise Exception("Processing failed")
    time.sleep(1)

# Get results
result_response = requests.get(f"http://localhost:8000/api/v1/results/{result_id}")
structured_data = result_response.json()
```

## Direct Model Usage

### Load Fine-Tuned Model

```python
from transformers import AutoModelForCausalLM, AutoProcessor
from PIL import Image
import torch

# Load model
model_path = "./finetuned_paddleocr_invoice_model/final_model"
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    trust_remote_code=True,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)

# Load and process image
image = Image.open("invoice.jpg").convert("RGB")

# Create prompt
messages = [
    {
        "role": "user",
        "content": [
            {"type": "image", "image": image},
            {
                "type": "text",
                "text": "Extract invoice information from this document. "
                        "Return structured JSON with vendor, invoice_number, "
                        "line_items, and financial_summary."
            },
        ],
    }
]

# Process
inputs = processor(text=[messages], images=[image], return_tensors="pt")
inputs = {k: v.to(model.device) for k, v in inputs.items()}

# Generate
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=1024,
        temperature=0.1,  # Low temperature for deterministic output
        do_sample=False
    )

# Decode response
response = processor.decode(outputs[0], skip_special_tokens=True)

# Parse JSON
import json
# Extract JSON from response (model may add extra text)
json_start = response.find("{")
json_end = response.rfind("}") + 1
if json_start >= 0 and json_end > json_start:
    json_str = response[json_start:json_end]
    structured_data = json.loads(json_str)
else:
    raise ValueError("Could not extract JSON from model response")
```

## Using the Document Processor

The `FinancialDocumentProcessor` class provides a high-level interface:

```python
from app.core.document_processor import FinancialDocumentProcessor
from app.config.settings import load_config

# Initialize
config = load_config()
processor = FinancialDocumentProcessor(config)

# Process document
with open("invoice.pdf", "rb") as f:
    file_content = f.read()

result = await processor.process_document(file_content)

# Access structured data
print(f"Vendor: {result.vendor.name}")
print(f"Invoice Number: {result.invoice_number}")
print(f"Total: {result.financial_summary.grand_total} {result.financial_summary.currency}")

# Check validation
if result.validation.is_valid:
    print("✓ Document passes validation")
else:
    print("✗ Validation errors:")
    for error in result.validation.errors:
        print(f"  - {error}")

# Export to JSON
import json
with open("output.json", "w") as f:
    json.dump(result.to_dict(), f, indent=2)
```

## Input Formats

Supported input formats:
- **PDF**: Multi-page documents (each page processed separately)
- **Images**: PNG, JPG, JPEG, TIFF
- **File size**: Recommended < 10MB per document
- **Resolution**: Minimum 150 DPI, recommended 300 DPI

## Output Schema

The output follows this canonical schema:

```json
{
  "document_type": "invoice",
  "vendor": {
    "name": "TechCorp Inc.",
    "address": {...},
    "contact": {...}
  },
  "client": {...},
  "invoice_number": "INV-2024-001",
  "issue_date": "2024-03-15",
  "due_date": "2024-04-14",
  "line_items": [
    {
      "description": "Item name",
      "quantity": 2.0,
      "unit_price": 50.0,
      "line_total": 100.0
    }
  ],
  "financial_summary": {
    "subtotal": 100.0,
    "tax_rate": 0.1,
    "tax_amount": 10.0,
    "grand_total": 110.0,
    "currency": "USD"
  },
  "validation": {
    "is_valid": true,
    "errors": [],
    "confidence": 0.95
  },
  "metadata": {
    "processing_date": "2024-03-15T10:30:00Z",
    "model_version": "paddleocr-vl-financial-v1.0"
  }
}
```

## Performance

- **Average Processing Time**: 2.8 seconds per document (on GPU)
- **Throughput**: ~350 documents/hour (single GPU)
- **Memory Usage**: ~8GB VRAM for inference
- **CPU Usage**: Moderate (mainly for preprocessing and post-processing)

## Error Handling

### Common Errors

1. **Invalid File Format**
   ```python
   # Ensure file is PDF or image
   if not file_path.endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff')):
       raise ValueError("Unsupported file format")
   ```

2. **Low Image Quality**
   - Model may return lower confidence scores
   - Fields with confidence < 0.8 are flagged for review

3. **Unparseable JSON**
   ```python
   try:
       data = json.loads(response)
   except json.JSONDecodeError:
       # Retry with different prompt or flag for manual review
       pass
   ```

### Validation Errors

The model performs business logic validation:
- **Arithmetic Checks**: Line totals = quantity × unit_price
- **Date Logic**: Issue date ≤ due date
- **Currency Consistency**: All amounts in same currency

If validation fails, the `validation.errors` field contains details.

## Batch Processing

```python
import asyncio
from pathlib import Path

async def process_batch(directory: Path):
    processor = FinancialDocumentProcessor(load_config())
    results = []
    
    for file_path in directory.glob("*.pdf"):
        with open(file_path, "rb") as f:
            content = f.read()
        result = await processor.process_document(content)
        results.append({
            "file": file_path.name,
            "result": result.to_dict(),
            "valid": result.validation.is_valid
        })
    
    return results

# Run batch processing
directory = Path("./invoices")
results = asyncio.run(process_batch(directory))
```

## Advanced Usage

### Custom Prompts

For region-specific extraction:

```python
from app.core.models.paddleocr_vl_service import PaddleOCRVLService

service = PaddleOCRVLService(config)

# Extract vendor block specifically
vendor_result = await service.parse_region(
    image_bytes,
    region_type="vendor_block",
    bbox={"x": 0, "y": 0, "width": 500, "height": 200}
)
```

### Confidence Thresholds

```python
# Filter results by confidence
high_confidence_fields = {
    k: v for k, v in result.to_dict().items()
    if v.get("confidence", 0) > 0.9
}
```

### Active Learning

Submit corrections for model improvement:

```python
# Submit correction
correction = {
    "invoice_number": "CORRECTED-INV-001",
    "line_items": [...]
}

requests.post(
    f"http://localhost:8000/api/v1/results/{result_id}/corrections",
    json={"correction": correction}
)
```

## Troubleshooting

### Model Not Loading

- Ensure model path is correct
- Check GPU memory (need ~8GB VRAM)
- Verify transformers version >= 4.35.0

### Low Accuracy

- Check image quality (minimum 150 DPI)
- Verify document type matches training data (invoices work best)
- Review confidence scores and flag low-confidence fields

### Slow Inference

- Use GPU for inference (10x faster than CPU)
- Reduce image resolution if acceptable
- Batch process multiple documents in parallel

## Next Steps

- See [Training Guide](../training/README.md) to fine-tune on your own data
- See [Evaluation Results](../evaluation/results.md) for performance benchmarks
- See main [README.md](../README.md) for complete documentation


