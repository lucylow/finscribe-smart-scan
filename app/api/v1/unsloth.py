"""
Unsloth API Endpoints

FastAPI endpoints for Unsloth inference integration.
Provides /v1/unsloth/infer endpoint for structured JSON extraction from OCR text.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...core.models.unsloth_service import get_unsloth_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/unsloth", tags=["unsloth"])


# Request/Response models
class OCRPayload(BaseModel):
    """Request payload for Unsloth inference."""
    ocr_text: str = Field(..., description="OCR-extracted text from document")
    doc_id: Optional[str] = Field(None, description="Optional document ID for tracking")
    instruction: Optional[str] = Field(
        None,
        description="Optional custom instruction prompt. If not provided, uses default JSON extraction instruction."
    )
    max_new_tokens: Optional[int] = Field(
        None,
        description="Maximum tokens to generate (overrides model default)"
    )
    temperature: Optional[float] = Field(
        None,
        description="Sampling temperature (overrides model default, 0.0 = deterministic)"
    )


class UnslothResponse(BaseModel):
    """Response model for Unsloth inference."""
    doc_id: Optional[str] = None
    parsed: dict = Field(..., description="Parsed JSON output from Unsloth model")
    model_available: bool = Field(..., description="Whether Unsloth model was loaded successfully")
    error: Optional[str] = Field(None, description="Error message if inference failed")


@router.post("/infer", response_model=UnslothResponse)
async def infer_with_unsloth(payload: OCRPayload):
    """
    Run Unsloth inference on OCR text to extract structured JSON.
    
    This endpoint acts as the reasoning/finalizer stage in the FinScribe pipeline.
    It takes OCR output and produces validated, structured JSON.
    
    Example request:
    ```json
    {
        "ocr_text": "Vendor: TechCorp Inc.\\nInvoice: INV-2024-001\\nDate: 2024-01-15\\n...",
        "doc_id": "doc-123"
    }
    ```
    
    Example response:
    ```json
    {
        "doc_id": "doc-123",
        "parsed": {
            "document_type": "invoice",
            "vendor": {"name": "TechCorp Inc."},
            "line_items": [...],
            "financial_summary": {...}
        },
        "model_available": true
    }
    ```
    """
    try:
        service = get_unsloth_service()
        
        # Run inference
        result = service.infer(
            ocr_text=payload.ocr_text,
            instruction=payload.instruction,
            max_new_tokens=payload.max_new_tokens,
            temperature=payload.temperature,
        )
        
        # Check for errors in result
        if result.get("_error"):
            error_msg = result.get("_error_message", "Unknown inference error")
            logger.error(f"Unsloth inference error for doc {payload.doc_id}: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Inference failed: {error_msg}"
            )
        
        return UnslothResponse(
            doc_id=payload.doc_id,
            parsed=result,
            model_available=service.is_available(),
            error=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Unsloth inference: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health")
async def unsloth_health():
    """
    Health check for Unsloth service.
    Returns whether the model is loaded and available.
    """
    try:
        service = get_unsloth_service()
        is_available = service.is_available()
        
        return {
            "status": "ok" if is_available else "model_not_loaded",
            "model_available": is_available,
            "model_dir": service.model_dir,
            "device": service.device
        }
    except Exception as e:
        logger.error(f"Error checking Unsloth health: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "model_available": False,
            "error": str(e)
        }


