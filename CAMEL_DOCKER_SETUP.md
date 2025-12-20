# Docker Compose Updates for CAMEL Integration

This document shows the exact changes needed to `docker-compose.yml` to enable CAMEL-AI integration.

## 1. Update Backend Service Environment Variables

Add these environment variables to the `backend` service:

```yaml
environment:
  # ... existing variables ...
  # CAMEL-AI configuration
  - PADDLEOCR_VLLM_URL=${PADDLEOCR_VLLM_URL:-http://localhost:8001/v1}
  - VALIDATOR_URL=http://mock_validator:8100/v1/validate
  - LLAMA_API_URL=${LLAMA_API_URL:-}
  - OPENAI_API_KEY=${OPENAI_API_KEY:-}
  - ACTIVE_LEARNING_FILE=/app/active_learning.jsonl
```

## 2. Update Backend Depends On

Add `mock_validator` to the backend's `depends_on` section:

```yaml
depends_on:
  redis:
    condition: service_healthy
  postgres:
    condition: service_healthy
  minio:
    condition: service_healthy
  mock_validator:
    condition: service_healthy
```

## 3. Add Mock Validator Service

Add this service definition after the `minio` service and before the `prometheus` service:

```yaml
  # Mock Validator Service (offline, deterministic validator for testing)
  mock_validator:
    build:
      context: ./mock_validator
      dockerfile: Dockerfile
    container_name: finscribe_mock_validator
    ports:
      - "8100:8100"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8100/health"]
      interval: 10s
      timeout: 5s
      retries: 5
```

## Complete Example

Here's what the updated sections should look like:

### Backend Service (updated)

```yaml
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - MODEL_MODE=mock
      - MAX_UPLOAD_MB=50
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://finscribe:finscribe@postgres:5432/finscribe
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
      - STORAGE_BUCKET=finscribe
      # CAMEL-AI configuration
      - PADDLEOCR_VLLM_URL=${PADDLEOCR_VLLM_URL:-http://localhost:8001/v1}
      - VALIDATOR_URL=http://mock_validator:8100/v1/validate
      - LLAMA_API_URL=${LLAMA_API_URL:-}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - ACTIVE_LEARNING_FILE=/app/active_learning.jsonl
    volumes:
      - ./active_learning.jsonl:/app/active_learning.jsonl
      - upload_staging:/tmp/finscribe_uploads
      - ./logs:/app/logs
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
      minio:
        condition: service_healthy
      mock_validator:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### Mock Validator Service (new)

```yaml
  mock_validator:
    build:
      context: ./mock_validator
      dockerfile: Dockerfile
    container_name: finscribe_mock_validator
    ports:
      - "8100:8100"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8100/health"]
      interval: 10s
      timeout: 5s
      retries: 5
```

## Verification

After making these changes, verify the setup:

```bash
# Start services
docker-compose up -d

# Check mock validator health
curl http://localhost:8100/health

# Check CAMEL health
curl http://localhost:8000/api/v1/camel/health

# Test invoice processing
curl -X POST "http://localhost:8000/api/v1/process_invoice" \
  -F "file=@examples/sample_invoice.jpg"
```

