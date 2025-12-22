# Implementation Guide: Remaining Tasks

This guide provides step-by-step instructions for completing the remaining refactoring tasks.

## Task 2: Async Task Queue Integration

### Current Status
- ✅ Celery tasks defined (`app/core/tasks.py`)
- ✅ Celery app configured (`app/core/celery_app.py`)
- ✅ Example async endpoint created (`app/api/v1/async_endpoints.py`)
- ⚠️ Need to integrate with existing endpoints

### Steps to Complete

1. **Update existing `/analyze` endpoint:**
   ```python
   # In app/api/v1/endpoints.py
   from ...core.tasks import process_document_task
   from ...core.job_manager import job_manager
   
   @router.post("/analyze", response_model=JobResponse, status_code=202)
   async def analyze_document(file: UploadFile = File(...)):
       job_id = str(uuid.uuid4())
       file_content = await file.read()
       
       # Create job
       job_manager.create_job(job_id, "received")
       
       # Enqueue task
       process_document_task.delay(job_id, file_content, file.filename)
       
       return JobResponse(
           job_id=job_id,
           status="received",
           message="Job queued",
           status_url=f"/api/v1/jobs/{job_id}"
       )
   ```

2. **Update job status in Celery task:**
   ```python
   # In app/core/tasks.py
   from ..job_manager import job_manager
   
   @celery_app.task(bind=True, name="process_document")
   def process_document_task(self, job_id, file_content, filename):
       try:
           job_manager.update_job_status(job_id, "processing", progress=10)
           # ... processing ...
           job_manager.update_job_status(job_id, "completed", progress=100, result_id=result_id)
       except Exception as e:
           job_manager.update_job_status(job_id, "failed", error=str(e))
           raise
   ```

3. **Register async endpoint in main.py:**
   ```python
   from .api.v1.async_endpoints import router as async_router
   app.include_router(async_router, prefix="/api/v1", tags=["async"])
   ```

## Task 5: Unsloth API Optimization

### Steps to Complete

1. **Load model at startup:**
   ```python
   # In unsloth_api/app/unsloth_api.py
   from fastapi import FastAPI
   from contextlib import asynccontextmanager
   
   model = None
   
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Startup: Load model
       global model
       model = load_unsloth_model()
       yield
       # Shutdown: Cleanup
       model = None
   
   app = FastAPI(lifespan=lifespan)
   ```

2. **Use provisioned concurrency:**
   - For serverless: Configure provisioned concurrency
   - For containers: Use always-on instances
   - For Kubernetes: Set min replicas > 0

3. **Implement model warming:**
   ```python
   # Warm up model on startup
   async def warmup_model():
       dummy_input = "Test input"
       _ = await model.generate(dummy_input)
   ```

## Task 6: Redis Caching Integration

### Steps to Complete

1. **Integrate cache in ExtractionService:**
   ```python
   # In app/core/services/extraction_service.py
   from ..cache import cache_service
   
   async def extract_from_document(self, file_content, filename):
       # Check OCR cache
       cached_ocr = await cache_service.get_ocr_result(file_content)
       if cached_ocr:
           logger.info("OCR cache hit")
           ocr_results = cached_ocr
       else:
           ocr_results = await self.ocr_service.parse_document(file_content)
           await cache_service.set_ocr_result(file_content, ocr_results)
       
       # Check extraction cache
       cached_extraction = await cache_service.get_extraction_result(ocr_results)
       if cached_extraction:
           logger.info("Extraction cache hit")
           enriched_data = cached_extraction
       else:
           enriched_data = await self.vlm_service.enrich_financial_data(ocr_results, file_content)
           await cache_service.set_extraction_result(ocr_results, enriched_data)
       
       return {...}
   ```

2. **Add cache metrics:**
   ```python
   # Track cache hit/miss rates
   from prometheus_client import Counter
   
   cache_hits = Counter('cache_hits_total', 'Total cache hits', ['cache_type'])
   cache_misses = Counter('cache_misses_total', 'Total cache misses', ['cache_type'])
   ```

## Task 9: Comprehensive Test Suite

### Steps to Complete

1. **Create test fixtures:**
   ```python
   # In tests/conftest.py
   import pytest
   from unittest.mock import Mock, AsyncMock
   
   @pytest.fixture
   def mock_ocr_service():
       service = Mock()
       service.parse_document = AsyncMock(return_value={
           "text": "Sample text",
           "tokens": [],
           "bboxes": []
       })
       return service
   
   @pytest.fixture
   def mock_validation_service():
       service = Mock()
       service.validate_extraction = Mock(return_value={
           "is_valid": True,
           "math_ok": True,
           "issues": []
       })
       return service
   ```

2. **Write unit tests:**
   ```python
   # In tests/unit/test_extraction_service.py
   import pytest
   from app.core.services.extraction_service import ExtractionService
   
   @pytest.mark.asyncio
   async def test_extraction_service(mock_ocr_service, mock_validation_service):
       service = ExtractionService()
       service.ocr_service = mock_ocr_service
       # ... test implementation
   ```

3. **Write integration tests:**
   ```python
   # In tests/integration/test_api_flow.py
   import pytest
   from httpx import AsyncClient
   from app.main import app
   
   @pytest.mark.asyncio
   async def test_document_upload_flow():
       async with AsyncClient(app=app, base_url="http://test") as client:
           # Upload document
           response = await client.post(
               "/api/v1/analyze-async",
               files={"file": ("test.pdf", b"fake pdf content")}
           )
           assert response.status_code == 202
           job_id = response.json()["job_id"]
           
           # Poll for status
           status_response = await client.get(f"/api/v1/jobs/{job_id}")
           assert status_response.status_code == 200
   ```

4. **Run coverage:**
   ```bash
   poetry run pytest --cov=app --cov-report=html
   # Aim for 80% coverage
   ```

## Task 11: PostgreSQL RLS Policies

### Steps to Complete

1. **Review existing policies:**
   ```sql
   -- Check existing policies
   SELECT * FROM pg_policies WHERE tablename = 'jobs';
   SELECT * FROM pg_policies WHERE tablename = 'results';
   ```

2. **Create RLS policies:**
   ```sql
   -- Enable RLS
   ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
   ALTER TABLE results ENABLE ROW LEVEL SECURITY;
   
   -- Policy: Users can only see their own jobs
   CREATE POLICY jobs_user_isolation ON jobs
       FOR ALL
       USING (user_id = current_setting('app.current_user_id')::uuid);
   
   -- Policy: Users can only see their own results
   CREATE POLICY results_user_isolation ON results
       FOR ALL
       USING (
           job_id IN (
               SELECT id FROM jobs 
               WHERE user_id = current_setting('app.current_user_id')::uuid
           )
       );
   ```

3. **Set user context in FastAPI:**
   ```python
   # In app/middleware/auth.py
   from fastapi import Request
   from starlette.middleware.base import BaseHTTPMiddleware
   
   class UserContextMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request: Request, call_next):
           user_id = get_user_id_from_token(request)
           if user_id:
               # Set PostgreSQL session variable
               await db.execute(
                   "SET app.current_user_id = :user_id",
                   {"user_id": user_id}
               )
           return await call_next(request)
   ```

## Additional Improvements

### TypeScript Interface Generation

1. **Install pydantic-to-typescript:**
   ```bash
   npm install --save-dev pydantic-to-typescript
   ```

2. **Generate types:**
   ```bash
   # Create script: scripts/generate-types.ts
   import { generate } from 'pydantic-to-typescript';
   
   generate({
     input: 'app/core/schemas',
     output: 'src/types/generated.ts'
   });
   ```

3. **Run in CI/CD:**
   ```yaml
   # .github/workflows/ci.yml
   - name: Generate TypeScript types
     run: npm run generate-types
   ```

### DVC Integration

1. **Initialize DVC:**
   ```bash
   dvc init
   ```

2. **Track training data:**
   ```bash
   dvc add data/training_data.jsonl
   dvc add data/validation_data.jsonl
   ```

3. **Record in model metadata:**
   ```python
   # In model training script
   import dvc.api
   
   dvc_commit = dvc.api.get_url("data/training_data.jsonl")
   model_metadata = {
       "training_data_dvc_commit": dvc_commit,
       "model_version": "v1.0.0"
   }
   ```

## Testing Checklist

- [ ] Unit tests for all services
- [ ] Integration tests for API flows
- [ ] Mock external services (Supabase, LLM APIs)
- [ ] Test error handling
- [ ] Test caching behavior
- [ ] Test async task queue
- [ ] Achieve 80% code coverage

## Deployment Checklist

- [ ] Set up Redis for caching
- [ ] Configure Celery workers
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure structured logging
- [ ] Review and test RLS policies
- [ ] Set up CI/CD pipeline
- [ ] Configure environment variables
- [ ] Test in staging environment

## Next Steps

1. Complete async task queue integration
2. Integrate Redis caching
3. Optimize Unsloth API
4. Expand test coverage
5. Review security policies
6. Set up monitoring and observability

