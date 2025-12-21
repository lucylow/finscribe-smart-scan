# Unsloth API Dockerfile
# GPU-enabled container for Unsloth inference service
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    build-essential \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip

# Install Unsloth and dependencies
# Note: This can take a while to build. For faster builds, consider using a pre-built image
RUN pip install --upgrade "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git" || \
    pip install --upgrade "unsloth @ git+https://github.com/unslothai/unsloth.git"

RUN pip install --upgrade "unsloth-zoo @ git+https://github.com/unslothai/unsloth_zoo.git" || true

# Install API dependencies
RUN pip install \
    transformers>=4.35.0 \
    accelerate>=0.24.0 \
    bitsandbytes>=0.41.0 \
    fastapi \
    uvicorn[standard] \
    aiofiles \
    python-multipart \
    huggingface_hub \
    torch>=2.0.0 \
    datasets \
    sentencepiece

WORKDIR /app

# Copy application code
COPY unsloth_api/app /app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run API server
CMD ["uvicorn", "unsloth_api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]


