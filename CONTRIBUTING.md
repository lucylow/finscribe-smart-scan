# Contributing to FinScribe Smart Scan

Thank you for your interest in contributing to FinScribe Smart Scan! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

1. [Local Setup](#local-setup)
2. [Development Workflow](#development-workflow)
3. [Code Style](#code-style)
4. [Testing](#testing)
5. [Architecture Overview](#architecture-overview)
6. [Submitting Changes](#submitting-changes)

## Local Setup

### Prerequisites

- **Python 3.11+** (required)
- **Node.js 18+** (for frontend development)
- **PostgreSQL 15+** (or use Docker Compose)
- **Redis** (or use Docker Compose)
- **Docker & Docker Compose** (recommended for quick start)

### Backend Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/finscribe-smart-scan.git
   cd finscribe-smart-scan
   ```

2. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies:**
   ```bash
   poetry install
   ```

4. **Activate the virtual environment:**
   ```bash
   poetry shell
   ```

5. **Set up environment variables:**
   Create a `.env` file in the root directory:
   ```bash
   DATABASE_URL=postgresql://user:password@localhost:5432/finscribe
   REDIS_URL=redis://localhost:6379/0
   MINIO_ENDPOINT=localhost:9000
   MINIO_ACCESS_KEY=minioadmin
   MINIO_SECRET_KEY=minioadmin
   STORAGE_BUCKET=finscribe
   MODEL_MODE=mock  # Use 'production' for real models
   ```

6. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

7. **Start the backend server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```

3. **Run linting:**
   ```bash
   npm run lint
   ```

### Docker Compose Setup (Recommended)

For a complete development environment:

```bash
docker-compose up --build
```

This starts:
- Backend API (port 8000)
- Frontend (port 5173)
- PostgreSQL (port 5432)
- Redis (port 6379)
- MinIO (ports 9000, 9001)
- Celery workers

## Development Workflow

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style guidelines below

3. **Run pre-commit hooks:**
   ```bash
   poetry run pre-commit run --all-files
   ```

4. **Run tests:**
   ```bash
   poetry run pytest
   ```

5. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

6. **Push and create a Pull Request**

## Code Style

### Python

We use strict code quality standards:

- **Black** for code formatting
- **isort** for import sorting
- **mypy** for type checking
- **Flake8** for linting

**Run code quality checks:**
```bash
# Format code
poetry run black .

# Sort imports
poetry run isort .

# Type check
poetry run mypy app data_pipeline finscribe

# Lint
poetry run flake8 app data_pipeline finscribe
```

**Pre-commit hooks** automatically run these checks. Install them:
```bash
poetry run pre-commit install
```

### TypeScript/JavaScript

- **ESLint** for code quality
- **Prettier** for formatting

**Run linting:**
```bash
npm run lint
```

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_validation.py

# Run with verbose output
poetry run pytest -v
```

### Test Coverage

We aim for **80% code coverage** minimum. Coverage reports are generated in `htmlcov/`.

### Writing Tests

- **Unit tests**: Test individual functions/classes in isolation
- **Integration tests**: Test full workflows (API → Queue → DB)

**Example unit test:**
```python
import pytest
from app.core.services.validation_service import ValidationService

def test_validation_service_arithmetic_check():
    service = ValidationService()
    # Test implementation
```

**Example integration test:**
```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_document_upload_flow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test full flow
```

### Mocking External Services

Always mock external dependencies:
- **Supabase**: Use `unittest.mock` or `pytest-mock`
- **LLM/OCR APIs**: Mock HTTP requests
- **Database**: Use test database or mocks

## Architecture Overview

### High-Level Flow

```
[Document Upload]
    ↓
[FastAPI Endpoint] → Returns 202 Accepted + job_id
    ↓
[Celery Task Queue] → Async processing
    ↓
[Extraction Service] → OCR + LLM extraction
    ↓
[Validation Service] → Business rule validation
    ↓
[Active Learning Service] → Log corrections
    ↓
[Database/Storage] → Persist results
    ↓
[Frontend Polling] → GET /api/v1/jobs/{job_id}
```

### Service Layer

The backend is organized into clear service boundaries:

- **ExtractionService**: Handles OCR and LLM extraction
- **ValidationService**: Validates business rules
- **ActiveLearningService**: Manages active learning data

### Data Contracts

All data structures use **Pydantic models** for type safety:
- `app/core/schemas/extraction.py`: Extraction result schemas
- `app/core/schemas/validation.py`: Validation result schemas
- `app/core/schemas/job.py`: Job management schemas

### Model Abstractions

Model providers are abstracted behind interfaces:
- `AbstractOCRProvider`: OCR provider interface
- `AbstractLLMExtractor`: LLM extractor interface

This allows easy swapping of models without changing core logic.

## Architecture Diagram

```mermaid
flowchart TB
    subgraph Frontend
        UI[React UI]
    end
    
    subgraph Backend
        API[FastAPI API]
        Queue[Redis Queue]
        Worker[Celery Workers]
    end
    
    subgraph Services
        Extract[Extraction Service]
        Validate[Validation Service]
        AL[Active Learning Service]
    end
    
    subgraph ML Services
        OCR[OCR Provider]
        LLM[LLM Extractor]
    end
    
    subgraph Storage
        DB[(PostgreSQL)]
        S3[(MinIO/S3)]
    end
    
    UI -->|POST /api/v1/analyze| API
    API -->|202 Accepted| UI
    API -->|Enqueue| Queue
    Queue -->|Process| Worker
    Worker --> Extract
    Extract --> OCR
    Extract --> LLM
    Extract --> Validate
    Validate --> AL
    Worker --> DB
    Worker --> S3
    UI -->|GET /api/v1/jobs/{id}| API
    API -->|Status| UI
```

## Submitting Changes

1. **Fork the repository** and create a feature branch

2. **Make your changes** following the guidelines above

3. **Write tests** for new functionality

4. **Update documentation** as needed

5. **Ensure all tests pass:**
   ```bash
   poetry run pytest
   npm run lint
   ```

6. **Commit with clear messages:**
   - Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, etc.
   - Example: `feat: add Redis caching for OCR results`

7. **Push to your fork** and create a Pull Request

8. **Wait for review** and address any feedback

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [React Documentation](https://react.dev/)

## Questions?

If you have questions or need help, please:
- Open an issue on GitHub
- Check existing documentation in `docs/`
- Review the codebase for examples

Thank you for contributing to FinScribe Smart Scan! 🎉

