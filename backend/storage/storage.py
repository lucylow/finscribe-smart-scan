# backend/storage/storage.py
from pathlib import Path
import json, time

BASE = Path("data")
JOB_DIR = BASE / "jobs"
ACTIVE_LEARNING_FILE = BASE / "active_learning.jsonl"

def ensure_dirs():
    BASE.mkdir(parents=True, exist_ok=True)
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    if not ACTIVE_LEARNING_FILE.exists():
        ACTIVE_LEARNING_FILE.write_text("")

def save_job_status(job_id: str, obj: dict):
    ensure_dirs()
    p = JOB_DIR / f"{job_id}.status.json"
    obj.setdefault("ts", time.time())
    p.write_text(json.dumps(obj, default=str))
    return str(p)

def save_job_result(job_id: str, result: dict):
    ensure_dirs()
    p = JOB_DIR / f"{job_id}.result.json"
    p.write_text(json.dumps(result, default=str))
    return str(p)

def append_active_learning(payload: dict):
    ensure_dirs()
    with open(ACTIVE_LEARNING_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.time(), "payload": payload}, default=str) + "\n")
    return True

# Backward compatibility
ensure_data_dir = ensure_dirs

