# ERNIE Integration Guide

This document describes the improved ERNIE integration in FinScribe Smart Scan, supporting both ERNIE 5 and ERNIE 4.5 models.

## Overview

The ERNIE integration has been enhanced to support:
- **ERNIE 5** (default, recommended for financial documents)
- **ERNIE 4.5 VL** (vision-language model with thinking capabilities)
- **ERNIE 4.5** (standard model)
- **HuggingFace integration** for model access
- **Automatic model version detection**
- **Fallback mechanisms** for reliability

## Configuration

### Environment Variables

```bash
# ERNIE Model Configuration
ERNIE_VLLM_URL=http://localhost:8002/v1          # vLLM server URL
ERNIE_MODEL_NAME=baidu/ERNIE-5                    # Model name (defaults to ERNIE 5)
ERNIE_MODEL_VERSION=auto                           # auto, ernie-5, ernie-4.5-vl, ernie-4.5
ERNIE_TIMEOUT=60                                  # Request timeout in seconds
ERNIE_MAX_RETRIES=3                               # Maximum retry attempts
ERNIE_ENABLE_THINKING=true                        # Enable thinking mode for supported models

# HuggingFace Integration (Optional)
HUGGINGFACE_TOKEN=your_token_here                 # HF token for private models
USE_HUGGINGFACE=false                             # Enable HuggingFace integration
```

### Model Selection

The system supports automatic model version detection based on the model name:

- `baidu/ERNIE-5` → ERNIE 5
- `baidu/ERNIE-4.5-VL-28B-A3B-Thinking` → ERNIE 4.5 VL
- `baidu/ERNIE-4.5-8B` → ERNIE 4.5

If `ERNIE_MODEL_VERSION=auto`, the system will detect the version from the model name.

## Supported Models

### ERNIE 5
- **Model Name**: `baidu/ERNIE-5`
- **Max Tokens**: 4096
- **Temperature**: 0.1
- **Thinking Mode**: Supported
- **Best For**: Financial document analysis, general purpose tasks
- **HuggingFace**: https://huggingface.co/collections/baidu/ernie-5

### ERNIE 4.5 VL
- **Model Name**: `baidu/ERNIE-4.5-VL-28B-A3B-Thinking`
- **Max Tokens**: 2048
- **Temperature**: 0.1
- **Thinking Mode**: Supported
- **Best For**: Vision-language tasks, OCR enhancement
- **HuggingFace**: https://huggingface.co/collections/baidu/ernie-45

### ERNIE 4.5
- **Model Name**: `baidu/ERNIE-4.5-8B`
- **Max Tokens**: 2048
- **Temperature**: 0.1
- **Thinking Mode**: Not supported
- **Best For**: Text-only tasks, faster inference

## Features

### 1. Automatic Model Detection
The system automatically detects the ERNIE model version from the model name and configures appropriate parameters.

### 2. HuggingFace Integration
- Access to ERNIE model collections on HuggingFace
- Support for private models with authentication
- Model information retrieval

### 3. Enhanced Error Handling
- JSON extraction from markdown code blocks
- Retry logic with exponential backoff
- Graceful fallback on errors
- Partial result handling

### 4. Model-Specific Optimizations
- ERNIE 5: Higher token limits for complex documents
- ERNIE 4.5 VL: Optimized for vision-language tasks
- Thinking mode enabled for supported models

## Usage Examples

### Basic Configuration (ERNIE 5)
```python
config = {
    "model_mode": "local",
    "ernie_vl": {
        "vllm_server_url": "http://localhost:8002/v1",
        "model_name": "baidu/ERNIE-5",
        "model_version": "auto",
        "timeout": 60,
        "enable_thinking": True
    }
}
```

### Using ERNIE 4.5 VL
```python
config = {
    "model_mode": "local",
    "ernie_vl": {
        "vllm_server_url": "http://localhost:8002/v1",
        "model_name": "baidu/ERNIE-4.5-VL-28B-A3B-Thinking",
        "model_version": "ernie-4.5-vl",
        "timeout": 60,
        "enable_thinking": True
    }
}
```

### HuggingFace Integration
```python
from app.core.models.huggingface_helper import HuggingFaceHelper

# Get model information
model_info = HuggingFaceHelper.get_model_info("baidu/ERNIE-5")
print(model_info["huggingface_url"])

# Get recommended model for use case
recommended = HuggingFaceHelper.get_recommended_model("financial_document")
```

## Response Format

The ERNIE VLM service returns structured data with the following format:

```json
{
    "status": "success",
    "model_version": "baidu/ERNIE-5",
    "model_family": "ernie-5",
    "structured_data": {
        "vendor_block": {...},
        "client_info": {...},
        "line_items": [...],
        "financial_summary": {...},
        "payment_terms": {...}
    },
    "validation_summary": {
        "is_valid": true,
        "math_verified": true,
        "issues": []
    },
    "confidence_scores": {
        "overall": 0.95,
        "vendor_block": 0.95,
        "client_info": 0.94,
        "line_items": 0.95,
        "financial_summary": 0.96
    },
    "latency_ms": 320,
    "token_usage": {
        "input": 1250,
        "output": 580,
        "total": 1830
    }
}
```

## Integration with PaddleOCR

The ERNIE models work in conjunction with PaddleOCR-VL:

1. **PaddleOCR-VL** extracts text and layout information
2. **ERNIE VLM** enriches the data with semantic understanding
3. **Validation** ensures data accuracy and consistency

## Troubleshooting

### Model Not Found
If the model is not found, check:
- vLLM server is running and accessible
- Model name matches the deployed model
- HuggingFace token is set if using private models

### JSON Parsing Errors
The system automatically attempts to extract JSON from markdown code blocks. If parsing fails, partial results are returned with the raw output.

### Timeout Issues
Increase `ERNIE_TIMEOUT` for complex documents or slower hardware.

## References

- ERNIE Official: https://ernie.baidu.com
- ERNIE 4.5 Blog: https://yiyan.baidu.com/blog/posts/ernie4.5/
- HuggingFace ERNIE Collection: https://huggingface.co/collections/baidu/ernie-45
- PaddleOCR: https://aistudio.baidu.com/paddleocr
- PaddleOCR-VL HuggingFace: https://huggingface.co/PaddlePaddle/PaddleOCR-VL

