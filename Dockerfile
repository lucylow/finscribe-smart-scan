# Use a lightweight Python image
FROM python:3.11-slim

# Install system dependencies for pdf2image, python-magic, and PaddleOCR
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libmagic1 \
    curl \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libpng-dev \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app
ENV MODEL_MODE=mock
ENV STORAGE_BASE=/data/storage
ENV CELERY_BROKER_URL=redis://redis:6379/0
WORKDIR $APP_HOME

# Optional: Install PaddleOCR for local OCR backend
# Set PADDLE_GPU=true to install GPU version
ARG PADDLE_GPU=false
ARG OCR_BACKEND=mock
ENV OCR_BACKEND=${OCR_BACKEND}

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Conditionally install PaddleOCR if OCR_BACKEND=paddle_local
RUN if [ "$OCR_BACKEND" = "paddle_local" ]; then \
      if [ "$PADDLE_GPU" = "true" ]; then \
        pip install paddlepaddle-gpu==2.5.0.post101 -f https://paddlepaddle.org.cn/whl/stable.html || \
        pip install paddlepaddle-gpu==2.5.0; \
      else \
        pip install paddlepaddle==2.5.0; \
      fi && \
      pip install paddleocr==2.6.1.0; \
    fi

# Copy the application code
COPY app $APP_HOME/app
COPY finscribe $APP_HOME/finscribe
COPY tests $APP_HOME/tests
COPY active_learning.jsonl $APP_HOME/active_learning.jsonl 2>/dev/null || true

# Create staging directory and storage directory
RUN mkdir -p /tmp/finscribe_uploads && \
    mkdir -p /data/storage

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
