"""Process invoice endpoint"""
import tempfile
import os
from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import Dict, Any
import logging

from backend.pipeline.invoice_pipeline import run_full_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/process_invoice", tags=["invoice"])


@router.post("")
async def process_invoice(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Process an invoice image/PDF.
    
    Returns structured JSON with:
    - invoice_id
    - structured_invoice
    - validation
    - confidence
    - latency_ms
    - fallback_used
    """
    temp_path = None
    
    try:
        # Read file bytes
        file_bytes = await file.read()
        
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        # Save to temporary file
        suffix = os.path.splitext(file.filename)[1] or ".png"
        temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False
        )
        temp_path = temp_file.name
        temp_file.write(file_bytes)
        temp_file.close()
        
        # Run pipeline
        logger.info(f"Processing invoice: {file.filename}")
        result = run_full_pipeline(temp_path, use_ernie=True)
        
        # Check for errors
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing invoice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass
