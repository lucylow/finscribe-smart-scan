# backend/api/process_invoice.py
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
import tempfile, os
from uuid import uuid4
import time

from backend.storage.storage import save_job_status, save_job_result, ensure_dirs
from backend.pipeline.ocr_pipeline import run_full_pipeline

router = APIRouter()

ensure_dirs()

def _save_tmp(upload: UploadFile):
    ext = os.path.splitext(upload.filename)[1] or ".png"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp.write(upload.file.read())
    tmp.flush()
    tmp.close()
    return tmp.name

def _background(job_id: str, image_path: str, use_ernie: bool):
    save_job_status(job_id, {"status":"processing", "ts": time.time()})
    try:
        res = run_full_pipeline(image_path, use_ernie=use_ernie)
        save_job_result(job_id, res)
        save_job_status(job_id, {"status":"done", "ts": time.time()})
    except Exception as e:
        save_job_status(job_id, {"status":"error", "error": str(e), "ts": time.time()})
    finally:
        try:
            os.remove(image_path)
        except Exception:
            pass

@router.post("/process_invoice")
async def process_invoice(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    # header toggles can be read by calling service; but for simplicity, we inspect filename or query
    try:
        tmp_path = _save_tmp(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to write uploaded file: {e}")
    job_id = uuid4().hex
    # choose to run synchronously in demo env if needed; otherwise background task
    # check X-SKIP-ERNIE header? Hard to get here; keep default use_ernie True if ERNIE_URL set
    use_ernie = bool(os.getenv("ERNIE_URL", "").strip())
    if background_tasks is None:
        # run inline (useful for tests)
        res = run_full_pipeline(tmp_path, use_ernie=use_ernie)
        return res
    else:
        save_job_status(job_id, {"status":"pending", "ts": time.time()})
        background_tasks.add_task(_background, job_id, tmp_path, use_ernie)
        return {"job_id": job_id, "status":"pending"}
