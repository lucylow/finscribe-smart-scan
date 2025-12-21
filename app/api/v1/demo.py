"""
Demo endpoints for quick E2E demo flow.
Provides simplified OCR and accept-and-queue endpoints for demo purposes.
"""
import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from ...ocr.backend import get_backend_from_env

logger = logging.getLogger(__name__)
router = APIRouter()

# Configuration
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
ACTIVE_LEARNING_FILE = DATA_DIR / "active_learning_queue.jsonl"


class OCRResponse(BaseModel):
    text: str
    regions: list
    tables: list = []
    meta: Dict[str, Any] = {}


class AcceptQueueRequest(BaseModel):
    doc_id: Optional[str] = None
    corrected: Dict[str, Any]
    meta: Optional[Dict[str, Any]] = None


@router.post("/demo/ocr", response_model=OCRResponse)
async def demo_ocr(file: UploadFile = File(...)):
    """
    Simplified OCR endpoint for demo purposes.
    Uses the configured OCR backend (mock, paddle_local, or paddle_hf).
    Returns OCR results in a format suitable for demo overlay visualization.
    """
    start_time = time.time()
    
    try:
        # Read image bytes
        image_bytes = await file.read()
        
        # Get OCR backend from environment
        backend = get_backend_from_env()
        
        # Run OCR
        ocr_result = backend.detect(image_bytes)
        
        # Convert OCRResult to response format
        # Map regions to format expected by frontend (with normalized bbox)
        regions_for_response = []
        
        for region in ocr_result.get("regions", []):
            # Normalize bbox to [x, y, width, height] format (0-1 normalized if needed)
            bbox = region.get("bbox", [])
            
            # If bbox is in pixel coordinates, we'll pass through (frontend can handle)
            # Format: [x, y, w, h] or [x1, y1, x2, y2]
            if len(bbox) >= 4:
                # Ensure format is [x, y, w, h]
                if len(bbox) == 4:
                    regions_for_response.append({
                        "type": region.get("type", "unknown"),
                        "bbox": bbox,
                        "text": region.get("text", ""),
                        "confidence": region.get("confidence", 0.0)
                    })
        
        duration = time.time() - start_time
        
        return OCRResponse(
            text=ocr_result.get("text", ""),
            regions=regions_for_response,
            tables=ocr_result.get("tables", []),
            meta={
                "backend": ocr_result.get("meta", {}).get("backend", "unknown"),
                "duration": duration,
                "latency_ms": duration * 1000,
                "filename": file.filename
            }
        )
        
    except Exception as e:
        logger.exception("Demo OCR failed")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


@router.post("/demo/accept_and_queue")
async def demo_accept_and_queue(payload: AcceptQueueRequest):
    """
    Accept corrected JSON and append to active learning queue (demo version).
    This endpoint is optimized for demo flow and writes to active_learning_queue.jsonl.
    """
    try:
        entry = {
            "doc_id": payload.doc_id,
            "corrected": payload.corrected,
            "meta": payload.meta or {},
            "timestamp": time.time(),
            "demo_mode": True
        }
        
        # Append to JSONL file
        with ACTIVE_LEARNING_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        
        logger.info(f"Demo: Queued correction for doc_id={payload.doc_id}")
        
        return {"ok": True, "queued": True, "file": str(ACTIVE_LEARNING_FILE)}
        
    except Exception as e:
        logger.exception("Failed to append to active learning queue")
        raise HTTPException(status_code=500, detail=f"Failed to queue: {str(e)}")


@router.get("/demo/metrics")
async def demo_metrics():
    """
    Get demo metrics including queue count.
    """
    queued_count = 0
    if ACTIVE_LEARNING_FILE.exists():
        try:
            with ACTIVE_LEARNING_FILE.open("r", encoding="utf-8") as f:
                queued_count = sum(1 for line in f if line.strip())
        except Exception as e:
            logger.warning(f"Failed to read queue file: {e}")
    
    return {
        "queued": queued_count,
        "demo_mode": os.getenv("DEMO_MODE", "true"),
        "ocr_backend": os.getenv("OCR_BACKEND", "mock"),
        "queue_file": str(ACTIVE_LEARNING_FILE)
    }

