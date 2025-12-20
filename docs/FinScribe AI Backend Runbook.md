# FinScribe AI Backend Runbook

This document outlines the deployment, operation, and maintenance of the FinScribe AI Backend service.

## 1. Overview

The backend is a FastAPI application that orchestrates the AI pipeline for financial document analysis. It exposes RESTful endpoints for document upload, analysis, model comparison, and job status tracking.

## 2. Technology Stack

- **Framework**: FastAPI (Python)
- **Asynchronous Tasks**: Python `BackgroundTasks` (Mocked for simplicity; production would use Redis Queue/Celery)
- **AI Services**: Mocked external services for PaddleOCR-VL and Semantic Parsing (LLM)
- **Containerization**: Docker

## 3. Deployment

The recommended deployment method is using Docker Compose.

### Prerequisites

- Docker and Docker Compose installed.

### Steps

1.  **Navigate to the root directory**:
    \`\`\`bash
    cd finscribe-ai-lovable/pure-white-zone
    \`\`\`

2.  **Build and run the services**:
    The `docker-compose.yml` file defines both the `backend` and `frontend` services.
    \`\`\`bash
    docker-compose up --build -d
    \`\`\`

3.  **Verify Status**:
    Check the health of the backend service:
    \`\`\`bash
    curl http://localhost:8000/api/v1/health
    # Expected output: {"status": "ok", "message": "FinScribe AI Backend is running."}
    \`\`\`

## 4. API Endpoints

The full OpenAPI specification is available at `http://localhost:8000/docs`.

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/health` | GET | Checks the service health. |
| `/api/v1/analyze` | POST | Uploads a document and queues an analysis job. Returns a `JobStatus`. |
| `/api/v1/compare` | POST | Uploads a document and queues a model comparison job. Returns a `JobStatus`. |
| `/api/v1/jobs/{job_id}` | GET | Retrieves the status and results of a queued job. |

## 5. Active Learning

The system supports active learning by logging all successfully processed documents to a file for future fine-tuning (LoRA SFT).

- **Log File**: `backend/active_learning.jsonl`
- **Format**: Each line is a JSON object containing the document ID, source file name, and the extracted data with lineage.

## 6. Maintenance and Troubleshooting

| Issue | Potential Cause | Resolution |
| :--- | :--- | :--- |
| **Backend 500 Error** | Mock AI services are not running (if implemented) or internal logic error. | Check backend logs (`docker logs finscribe-backend`). |
| **Job Status Stuck** | Background task failed or is taking too long. | Check backend logs. In a production system, check the task queue (e.g., Redis). |
| **Frontend CORS Error** | Frontend is accessing the wrong URL or port. | Verify `VITE_API_URL` in the frontend configuration matches the backend service. |
