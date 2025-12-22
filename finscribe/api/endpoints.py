# finscribe/api/endpoints.py
"""
Simple FastAPI demo endpoints to upload a file and enqueue OCR task.

POST /api/v1/analyze - accepts multipart file, stores to storage (staging), creates job_id,
                      enqueues finscribe.tasks.ocr_task and returns job_id + poll URL.

This endpoint uses the `get_storage` factory defined in finscribe.staging.
"""

import os
import uuid
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from ..staging import get_storage
from ..tasks import ocr_task  # requires finscribe.tasks to exist

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOGLEVEL", "INFO"))

app = FastAPI(title="FinScribe Smart Scan - Demo API")

storage = get_storage()
STAGING_PREFIX = os.getenv("STAGING_PREFIX", "staging")


@app.post("/api/v1/analyze")
async def analyze(file: UploadFile = File(...)):
    if file.content_type not in ("image/png", "image/jpeg", "application/pdf", "image/tiff"):
        raise HTTPException(status_code=400, detail="Unsupported file type")
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    # create a staging key
    fname = file.filename or f"upload-{uuid.uuid4().hex}.bin"
    staging_key = f"{STAGING_PREFIX}/{job_id}/{fname}"
    body = await file.read()
    storage.put_bytes(staging_key, body)
    # For demo: we expect 1 page per upload. In production you'd split PDFs to pages
    # and enqueue a per-page ocr_task. Here we enqueue one ocr_task with page_key = staging_key
    ocr_task.delay(job_id, staging_key, image_storage_key=staging_key)
    return JSONResponse({"job_id": job_id, "poll_url": f"/api/v1/jobs/{job_id}"})

