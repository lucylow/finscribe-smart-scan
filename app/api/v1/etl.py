"""
ETL Pipeline API Endpoints

Provides REST API for the production ETL pipeline.
"""
import os
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel

from data_pipeline.ingestion import ingest_from_local, ingest_from_bytes
from data_pipeline.preprocess import preprocess
from data_pipeline.ocr_client import run_ocr
from data_pipeline.semantic_parser import parse
from data_pipeline.normalizer import normalize_invoice_data
from data_pipeline.validator import validate
from data_pipeline.persistence import save_invoice

logger = logging.getLogger(__name__)
router = APIRouter()


class ETLIngestResponse(BaseModel):
    """Response model for ETL ingestion."""
    invoice_id: int
    validation: dict
    message: str


@router.post("/etl/ingest_local", response_model=ETLIngestResponse)
async def etl_ingest_local(path: str):
    """
    Ingest and process invoice from local file path.
    
    Args:
        path: Local file system path to invoice image/PDF
        
    Returns:
        ETLIngestResponse with invoice_id and validation results
    """
    try:
        # Extract
        src = ingest_from_local(path)
        pp = preprocess(src)
        ocr = run_ocr(pp)
        
        # Transform
        structured = parse(ocr)
        structured = normalize_invoice_data(structured)
        
        # Validate
        validation = validate(structured)
        
        # Load
        inv_id = save_invoice(structured, ocr, src)
        
        return ETLIngestResponse(
            invoice_id=inv_id,
            validation=validation,
            message="Invoice processed successfully"
        )
    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/etl/ingest_upload", response_model=ETLIngestResponse)
async def etl_ingest_upload(
    file: UploadFile = File(...),
    enable_denoise: bool = Form(False)
):
    """
    Ingest and process invoice from file upload.
    
    Args:
        file: Uploaded file
        enable_denoise: Whether to enable denoising in preprocessing
        
    Returns:
        ETLIngestResponse with invoice_id and validation results
    """
    try:
        # Read file bytes
        content = await file.read()
        
        # Extract
        src = ingest_from_bytes(content, file.filename)
        pp = preprocess(src, enable_denoise=enable_denoise)
        ocr = run_ocr(pp)
        
        # Transform
        structured = parse(ocr)
        structured = normalize_invoice_data(structured)
        
        # Validate
        validation = validate(structured)
        
        # Load
        inv_id = save_invoice(structured, ocr, src)
        
        return ETLIngestResponse(
            invoice_id=inv_id,
            validation=validation,
            message="Invoice processed successfully"
        )
    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/etl/health")
async def etl_health():
    """Health check for ETL pipeline."""
    return {
        "status": "ok",
        "ocr_backend": os.getenv("OCR_BACKEND", "local"),
        "vlm_endpoint": "configured" if os.getenv("VLM_ENDPOINT") else "not_configured"
    }

