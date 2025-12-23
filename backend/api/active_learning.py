# backend/api/active_learning.py
from fastapi import APIRouter, HTTPException, Request
from backend.storage.storage import append_active_learning

router = APIRouter()

@router.post("/active_learning")
async def push_active_learning(req: Request):
    try:
        payload = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")
    ok = append_active_learning(payload)
    return {"ok": ok}
