# backend/storage/storage.py
from pathlib import Path
import json
import time

BASE = Path("data")
JOB_DIR = BASE / "jobs"
ACTIVE_LEARNING_FILE = BASE / "active_learning.jsonl"

def ensure_data_dir():
    BASE.mkdir(parents=True, exist_ok=True)
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    if not ACTIVE_LEARNING_FILE.exists():
        ACTIVE_LEARNING_FILE.write_text("")

def save_job_status(job_id: str, status_obj: dict):
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    p = JOB_DIR / f"{job_id}.status.json"
    status_obj.setdefault("ts", time.time())
    p.write_text(json.dumps(status_obj, default=str))

def save_job_result(job_id: str, result: dict):
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    p = JOB_DIR / f"{job_id}.result.json"
    p.write_text(json.dumps(result, default=str))

