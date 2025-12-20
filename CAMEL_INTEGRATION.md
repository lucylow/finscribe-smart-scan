# CAMEL-AI Integration Guide for FinScribe

This document describes the CAMEL-AI integration into the FinScribe smart scan stack, providing agent-based orchestration for OCR and validation workflows.

## Overview

CAMEL-AI (Communicative Agents for "Mind" Exploration of Large Language Model Society) enables intelligent agent-based orchestration of document processing. This integration allows FinScribe to:

- Use CAMEL ChatAgents to orchestrate OCR and validation workflows
- Expose OCR and validation services as FunctionTools
- Enable agents to automatically call tools when needed
- Support multiple model backends (OpenAI, vLLM, local models)

## Architecture

```
┌─────────────────┐
│  FastAPI        │
│  /process_invoice│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CAMEL Agent    │
│  (ChatAgent)    │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐  ┌────────────┐
│  OCR   │  │  Validator │
│  Tool  │  │  Tool      │
└────┬───┘  └─────┬──────┘
     │            │
     ▼            ▼
┌────────┐  ┌────────────┐
│ OCR    │  │ Mock/LLM   │
│ Service│  │ Validator  │
└────────┘  └────────────┘
```

## Components

### 1. CAMEL Tools (`camel_tools.py`)

Wraps existing FinScribe services as CAMEL FunctionTools:

- `call_ocr_file_bytes()`: Calls OCR service with file bytes
- `call_validator()`: Calls validation service to correct JSON
- `llama_validate()`: Optional LLM-based validation

### 2. CAMEL Agent (`camel_agent.py`)

Creates and configures a CAMEL ChatAgent with:
- System message defining agent role
- OCR and validation tools
- Model backend (OpenAI, vLLM, or dummy fallback)

### 3. FastAPI Endpoints (`app/api/v1/camel_endpoints.py`)

- `POST /api/v1/process_invoice`: Process invoice using CAMEL agent
- `GET /api/v1/camel/health`: Health check for CAMEL service

### 4. Mock Validator Service (`mock_validator/`)

Offline, deterministic validator for testing:
- No LLM required
- Arithmetic validation
- Deterministic corrections
- Perfect for CI/CD and development

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `camel-ai[all]>=0.2.5` - CAMEL-AI framework
- `fastmcp` - For MCP server support (optional)

### 2. Generate Sample Invoice

```bash
make generate-sample
# Creates examples/sample_invoice.jpg
```

Or manually:
```bash
python examples/generate_sample_invoice.py
```

### 3. Start Services

```bash
# Start all services (including mock_validator)
make up

# Or manually:
docker-compose up -d
```

### 4. Test CAMEL Integration

```bash
# Test with sample invoice
make test-camel

# Or manually:
curl -X POST "http://localhost:8000/api/v1/process_invoice" \
  -F "file=@examples/sample_invoice.jpg" \
  -H "accept: application/json"
```

### 5. Check Health

```bash
make health
```

## Configuration

### Environment Variables

Set in `docker-compose.yml` or `.env`:

```bash
# OCR Service URL (default: http://localhost:8001/v1)
PADDLEOCR_VLLM_URL=http://localhost:8001/v1

# Validator Service URL (default: http://mock_validator:8100/v1/validate)
VALIDATOR_URL=http://mock_validator:8100/v1/validate

# Optional: LLM API for validation
LLAMA_API_URL=http://localhost:8000/v1/chat/completions
LLAMA_MODEL=finscribe-llama
LLAMA_API_KEY=your-key-here

# Optional: OpenAI API key for CAMEL agent model
OPENAI_API_KEY=sk-...

# Active learning queue file
ACTIVE_LEARNING_FILE=/app/active_learning.jsonl
```

### Model Backend Selection

CAMEL agent automatically selects model backend in this order:

1. **OpenAI** (if `OPENAI_API_KEY` is set)
   - Uses GPT-4o or GPT-4
   - Best for production

2. **vLLM** (if `VLLM_API_URL` or `LLAMA_API_URL` is set)
   - Local or remote vLLM server
   - Good for cost-effective production

3. **Dummy** (fallback)
   - Tool-only processing
   - No LLM calls
   - Good for testing tool flow

## Usage Examples

### Basic Invoice Processing

```python
import requests

# Upload invoice file
with open("invoice.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/process_invoice",
        files={"file": f},
        params={"doc_id": "invoice-123"}
    )

result = response.json()
print(result["corrected"])  # Corrected invoice JSON
```

### Using CAMEL Agent Directly

```python
from camel_agent import make_agent
from camel.messages import BaseMessage

# Create agent
agent = make_agent()

# Process invoice
prompt = BaseMessage.make_user_message(
    content="Process this invoice: extract text and validate JSON structure."
)

response = agent.step(prompt)
print(response.msgs[0].content)
```

### Custom Tools

You can add custom tools to the CAMEL agent:

```python
from camel.toolkits import FunctionTool

def my_custom_tool(input: str) -> str:
    """Custom tool description."""
    return f"Processed: {input}"

custom_tool = FunctionTool(my_custom_tool)

# Add to agent tools list in camel_agent.py
```

## Mock Validator

The mock validator (`mock_validator/`) provides offline validation for testing:

- **Deterministic**: Same input → same output
- **Fast**: No LLM calls
- **Arithmetic validation**: Checks subtotal + tax = total
- **Auto-correction**: Fixes arithmetic mismatches

### Testing Mock Validator

```bash
curl -X POST "http://localhost:8100/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_text": "Subtotal: 1000.00\nTax: 100.00\nTotal: 1100.00",
    "doc_id": "test-1"
  }'
```

## Integration with Existing FinScribe Services

### OCR Service Integration

CAMEL tools call existing OCR services via HTTP:
- PaddleOCR-VL vLLM endpoint
- ERNIE-VL endpoint
- Mock OCR service

Configure via `PADDLEOCR_VLLM_URL` environment variable.

### Validation Integration

CAMEL tools can call:
1. **Mock Validator** (default for testing)
2. **LLaMA-Factory/Unsloth** endpoints
3. **Custom validation services**

Configure via `VALIDATOR_URL` environment variable.

## Docker Services

### Services Added

1. **mock_validator**: Offline validator service
   - Port: 8100
   - Health: `http://localhost:8100/health`

2. **backend** (updated): Now includes CAMEL endpoints
   - CAMEL health: `http://localhost:8000/api/v1/camel/health`
   - Process invoice: `http://localhost:8000/api/v1/process_invoice`

## Active Learning

Corrected invoices are automatically saved to the active learning queue:

- File: `active_learning.jsonl`
- Format: JSONL with prompt/completion pairs
- Used for fine-tuning models

## Troubleshooting

### CAMEL Agent Not Initializing

1. Check dependencies: `pip install 'camel-ai[all]'`
2. Check environment variables (especially API keys)
3. Review logs: `docker-compose logs backend`

### Tools Not Being Called

1. Ensure agent system message mentions using tools
2. Check tool registration in `camel_agent.py`
3. Review agent step logs

### Mock Validator Not Responding

1. Check service is running: `docker-compose ps mock_validator`
2. Check health: `curl http://localhost:8100/health`
3. Review logs: `docker-compose logs mock_validator`

## Production Considerations

1. **Model Selection**: Use OpenAI or vLLM for production (not dummy)
2. **Authentication**: Add API key authentication to endpoints
3. **Rate Limiting**: Implement rate limiting for `/process_invoice`
4. **Monitoring**: Add Prometheus metrics for agent calls
5. **Error Handling**: Review and enhance error handling
6. **Security**: Secure API keys and credentials

## References

- [CAMEL-AI Documentation](https://docs.camel-ai.org)
- [CAMEL-AI GitHub](https://github.com/camel-ai/camel)
- [MCP Protocol](https://mcp.camel-ai.org/)
- [FunctionTool Documentation](https://docs.camel-ai.org/api/toolkits.html)

## Next Steps

1. **MCP Integration**: Expose MinIO/Postgres as MCP servers
2. **Multi-Agent**: Use multiple specialized agents
3. **Advanced Tools**: Add more specialized tools (DB queries, file operations)
4. **Streaming**: Implement streaming responses for long-running tasks
5. **Agent Memory**: Add conversation memory for multi-step workflows

