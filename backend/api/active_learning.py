# backend/api/active_learning.py
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json, time
from backend.storage.storage import ACTIVE_LEARNING_FILE, ensure_data_dir

router = APIRouter()

ensure_data_dir()

@router.post("/active_learning")
async def push_active_learning(payload: dict):
    """Append corrected invoice JSON to active learning queue (JSONL)."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be JSON object")
    entry = {"ts": time.time(), "payload": payload}
    with open(ACTIVE_LEARNING_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    return {"ok": True, "saved": True}
