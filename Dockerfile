# Use a lightweight Python image
FROM python:3.11-slim

# Install system dependencies for pdf2image and python-magic
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app
ENV MODEL_MODE=mock
WORKDIR $APP_HOME

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app $APP_HOME/app
COPY active_learning.jsonl $APP_HOME/active_learning.jsonl

# Create staging directory
RUN mkdir -p /tmp/finscribe_uploads

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
