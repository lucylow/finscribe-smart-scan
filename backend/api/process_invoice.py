# backend/api/process_invoice.py
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from uuid import uuid4
from pathlib import Path
import shutil, os, time, json

from backend.pipeline.ocr_pipeline import run_full_pipeline
from backend.storage.storage import save_job_status, save_job_result, JOB_DIR

router = APIRouter()

# Ensure job directory exists
JOB_DIR.mkdir(parents=True, exist_ok=True)

def _save_file_tmp(upload: UploadFile) -> Path:
    ext = Path(upload.filename).suffix or ".png"
    job_tmp = JOB_DIR / f"tmp_{uuid4().hex}{ext}"
    with open(job_tmp, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return job_tmp

def _background_process(job_id: str, image_path: str):
    save_job_status(job_id, {"status": "processing", "ts": time.time()})
    try:
        result = run_full_pipeline(image_path)
        save_job_result(job_id, result)
        save_job_status(job_id, {"status": "done", "ts": time.time()})
    except Exception as e:
        save_job_status(job_id, {"status": "error", "error": str(e), "ts": time.time()})
    finally:
        try:
            os.remove(image_path)
        except Exception:
            pass

@router.post("/submit")
async def submit_invoice(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """Accept file, store temporarily, kick background job, return job_id."""
    if file is None:
        raise HTTPException(status_code=400, detail="file required")
    tmp_path = _save_file_tmp(file)
    job_id = uuid4().hex
    # initial status
    save_job_status(job_id, {"status": "pending", "ts": time.time()})
    # run background
    background_tasks.add_task(_background_process, job_id, str(tmp_path))
    return {"job_id": job_id, "status": "pending"}

@router.get("/status/{job_id}")
async def job_status(job_id: str):
    s = (JOB_DIR / f"{job_id}.status.json")
    if not s.exists():
        return {"status": "not_found"}
    return json.loads(s.read_text())

@router.get("/result/{job_id}")
async def job_result(job_id: str):
    r = (JOB_DIR / f"{job_id}.result.json")
    if not r.exists():
        return {"status": "not_ready"}
    return json.loads(r.read_text())
