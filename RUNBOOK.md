# FinScribe Backend Runbook

This runbook provides instructions for running, testing, and operating the FinScribe backend system.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ (for local development)
- Access to required environment variables

## Quick Start

### 1. Start the Stack

```bash
# Start all services (backend, worker, redis, postgres, minio)
docker-compose up -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
```

### 2. Initialize Database

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Or if running locally
export DATABASE_URL=postgresql://finscribe:finscribe@localhost:5432/finscribe
alembic upgrade head
```

### 3. Verify Services

```bash
# Check backend health
curl http://localhost:8000/api/v1/health

# Check metrics endpoint
curl http://localhost:8000/api/v1/metrics

# Check MinIO console (optional)
open http://localhost:9001
# Login: minioadmin / minioadmin
```

## Upload Sample Document

### Using curl

```bash
# Upload a document for analysis
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@path/to/your/invoice.pdf"

# Response will include job_id and poll_url:
# {
#   "job_id": "uuid-here",
#   "poll_url": "/api/v1/jobs/uuid-here",
#   "status": "queued"
# }
```

### Poll Job Status

```bash
# Replace JOB_ID with the job_id from the upload response
JOB_ID="your-job-id-here"

# Poll job status
curl http://localhost:8000/api/v1/jobs/$JOB_ID

# Response includes:
# {
#   "job_id": "...",
#   "status": "processing|completed|failed",
#   "progress": 0-100,
#   "stage": "ocr|parse|validate|...",
#   "result": {...}  # Only when completed
# }
```

### Fetch Result

```bash
# Once job is completed, get the result
RESULT_ID="result-id-from-job-result"

curl http://localhost:8000/api/v1/results/$RESULT_ID
```

## Service Architecture

### Services

1. **backend** (port 8000): FastAPI application serving REST API
2. **worker**: Celery worker processing background tasks
3. **redis** (port 6379): Message broker and cache
4. **postgres** (port 5432): Primary database
5. **minio** (ports 9000, 9001): Object storage (S3-compatible)
6. **prometheus** (port 9090, optional): Metrics collection
7. **grafana** (port 3000, optional): Metrics visualization

### Task Queue

Tasks are distributed across queues:
- **cpu**: CPU-bound tasks (ingest, preprocess, postprocess, validate, index)
- **gpu**: GPU-bound tasks (ocr, vlm_parse)

## Environment Variables

Key environment variables:

```bash
# Model configuration
MODEL_MODE=mock  # mock|local|remote

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# Object Storage (MinIO/S3)
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
STORAGE_BUCKET=finscribe

# File upload limits
MAX_UPLOAD_MB=50

# Security (optional)
RBAC_ENABLED=false
PII_REDACTION_ENABLED=false
AUDIT_LOG_FILE=./logs/audit.log
```

## Database Operations

### Run Migrations

```bash
# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec backend alembic upgrade head

# Rollback migration
docker-compose exec backend alembic downgrade -1
```

### Database Backup

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U finscribe finscribe > backup.sql

# Restore
docker-compose exec -T postgres psql -U finscribe finscribe < backup.sql
```

## Monitoring & Metrics

### Prometheus (optional)

```bash
# Start with monitoring profile
docker-compose --profile monitoring up -d

# Access Prometheus
open http://localhost:9090

# Query metrics
# Example: finscribe_jobs_completed_total
```

### Grafana (optional)

```bash
# Start with monitoring profile
docker-compose --profile monitoring up -d

# Access Grafana
open http://localhost:3000
# Login: admin / admin
```

### View Metrics

```bash
# Prometheus metrics endpoint
curl http://localhost:8000/api/v1/metrics

# Common metrics:
# - finscribe_jobs_submitted_total
# - finscribe_jobs_completed_total
# - finscribe_ocr_latency_seconds
# - finscribe_vlm_latency_seconds
# - finscribe_task_latency_seconds
```

## Active Learning

### Export Active Learning Data

```bash
# Export as JSONL (default)
curl http://localhost:8000/api/v1/admin/active_learning/export?format=jsonl

# Export as JSON
curl http://localhost:8000/api/v1/admin/active_learning/export?format=json
```

### Submit Corrections

```bash
# Submit corrections for a result
curl -X POST http://localhost:8000/api/v1/results/$RESULT_ID/corrections \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_number": "corrected-value",
    "total": 1234.56
  }'
```

## Troubleshooting

### Check Service Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f worker

# Last 100 lines
docker-compose logs --tail=100 worker
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose exec postgres pg_isready -U finscribe

# Connect to database
docker-compose exec postgres psql -U finscribe finscribe

# Check tables
\dt
SELECT COUNT(*) FROM jobs;
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose exec redis redis-cli ping

# View queue info
docker-compose exec redis redis-cli LLEN celery
```

### Worker Issues

```bash
# Check worker status
docker-compose exec worker celery -A app.core.celery_app inspect active

# Check registered tasks
docker-compose exec worker celery -A app.core.celery_app inspect registered

# Purge queue (careful!)
docker-compose exec worker celery -A app.core.celery_app purge
```

### Storage Issues

```bash
# Check MinIO is accessible
curl http://localhost:9000/minio/health/live

# List objects (using MinIO client or AWS CLI)
# Install: brew install minio/stable/mc
mc alias set local http://localhost:9000 minioadmin minioadmin
mc ls local/finscribe
```

## Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=sqlite:///./finscribe.db  # Or use Postgres
export REDIS_URL=redis://localhost:6379/0
export MODEL_MODE=mock

# Run migrations
alembic upgrade head

# Run backend
uvicorn app.main:app --reload --port 8000

# Run worker (in separate terminal)
celery -A app.core.celery_app worker --loglevel=info
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_validation.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run integration tests
pytest tests/integration/
```

### Code Quality

```bash
# Format code
black app tests

# Lint
flake8 app

# Type check
mypy app --ignore-missing-imports
```

## Production Deployment

### Key Considerations

1. **Secrets Management**: Use environment variables or secrets manager (AWS Secrets Manager, HashiCorp Vault)
2. **Database**: Use managed PostgreSQL (AWS RDS, Google Cloud SQL)
3. **Object Storage**: Use S3 or compatible service
4. **Redis**: Use managed Redis (AWS ElastiCache, Redis Cloud)
5. **SSL/TLS**: Enable HTTPS with reverse proxy (nginx, traefik)
6. **Monitoring**: Enable Prometheus and Grafana profiles
7. **Logging**: Configure centralized logging (ELK stack, CloudWatch)
8. **Backup**: Regular database and storage backups
9. **Scaling**: Scale workers horizontally based on load

### Docker Production Build

```bash
# Build production image
docker build -t finscribe-backend:latest .

# Run with production config
docker-compose -f docker-compose.prod.yml up -d
```

### Health Checks

```bash
# Application health
curl http://localhost:8000/api/v1/health

# Metrics endpoint
curl http://localhost:8000/api/v1/metrics

# Database connectivity
docker-compose exec backend python -c "from app.db import SessionLocal; SessionLocal()"

# Worker connectivity
docker-compose exec worker celery -A app.core.celery_app inspect ping
```

## Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Review this runbook
3. Check GitHub issues
4. Contact development team
