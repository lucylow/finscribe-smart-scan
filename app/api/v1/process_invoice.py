"""
Unified AI Gateway - /process_invoice Endpoint

This endpoint integrates:
1. PaddleOCR-VL (real OCR)
2. Unsloth Fine-Tuned LLaMA (field extraction)
3. CAMEL Agents (multi-agent verification & reasoning)

Returns a unified response that the frontend consumes.
"""
import os
import json
import time
import logging
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

# Import services
try:
    from app.core.models.unsloth_service import get_unsloth_service
    UNSLOTH_AVAILABLE = True
except ImportError:
    UNSLOTH_AVAILABLE = False
    logging.warning("Unsloth service not available")

try:
    from app.agents.camel_invoice import run_camel_agents
    CAMEL_AVAILABLE = True
except ImportError:
    CAMEL_AVAILABLE = False
    logging.warning("CAMEL agents not available")

try:
    from camel_tools import call_ocr_file_bytes
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logging.warning("OCR tools not available")

from app.parsers.json_parser import safe_json_parse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/process_invoice")
async def process_invoice(file: UploadFile = File(...)):
    """
    Unified invoice processing endpoint.
    
    Flow:
    1. OCR: Extract text from invoice image/PDF
    2. Unsloth: Extract structured JSON from OCR text
    3. CAMEL Agents: Multi-agent validation and reasoning
    4. Return: Unified response with OCR preview, structured invoice, and CAMEL analysis
    
    Returns:
        {
            "invoice_id": "uuid",
            "ocr_preview": "...raw text...",
            "structured_invoice": { ... },
            "camel_analysis": {
                "issues": [],
                "confidence": 0.97,
                "notes": "Totals validated, tax consistent"
            },
            "latency_ms": {
                "ocr": 480,
                "llm": 720,
                "agents": 310
            }
        }
    """
    invoice_id = str(uuid.uuid4())
    
    try:
        # Read file
        file_bytes = await file.read()
        
        # ========================================================================
        # Step 1: OCR Processing
        # ========================================================================
        ocr_start = time.time()
        ocr_text = ""
        
        if OCR_AVAILABLE:
            try:
                ocr_resp = call_ocr_file_bytes(file_bytes, filename=file.filename or "invoice.png")
                ocr_text = ocr_resp.get("text", "") or ocr_resp.get("ocr_text", "")
                if not ocr_text:
                    # Try to extract from structured data
                    ocr_data = ocr_resp.get("data") or ocr_resp.get("structured_data") or {}
                    if isinstance(ocr_data, dict):
                        # Try to reconstruct text from structured data
                        ocr_text = json.dumps(ocr_data, indent=2)
            except Exception as e:
                logger.warning(f"OCR processing failed: {e}, using fallback")
                ocr_text = f"[OCR Error: {str(e)}]"
        else:
            ocr_text = "[OCR service not available - using mock]"
            logger.warning("OCR service not available, using mock text")
        
        ocr_latency = int((time.time() - ocr_start) * 1000)
        
        # ========================================================================
        # Step 2: Unsloth LLM Extraction
        # ========================================================================
        llm_start = time.time()
        structured_invoice = {}
        
        if UNSLOTH_AVAILABLE and ocr_text and not ocr_text.startswith("[OCR Error"):
            try:
                unsloth_service = get_unsloth_service()
                llm_result = unsloth_service.infer(
                    ocr_text=ocr_text,
                    max_new_tokens=1024,
                    temperature=0.0
                )
                
                # Check for errors
                if llm_result.get("_error") or llm_result.get("_parse_error"):
                    logger.warning(f"Unsloth inference error: {llm_result.get('_error_message', 'Unknown error')}")
                    # Use fallback structure
                    structured_invoice = _create_fallback_invoice(ocr_text)
                else:
                    structured_invoice = llm_result
            except Exception as e:
                logger.error(f"Unsloth inference failed: {e}", exc_info=True)
                structured_invoice = _create_fallback_invoice(ocr_text)
        else:
            logger.warning("Unsloth not available or OCR failed, using fallback")
            structured_invoice = _create_fallback_invoice(ocr_text)
        
        llm_latency = int((time.time() - llm_start) * 1000)
        
        # ========================================================================
        # Step 3: CAMEL Multi-Agent Analysis
        # ========================================================================
        agents_start = time.time()
        camel_analysis = {
            "issues": [],
            "confidence": 0.85,
            "notes": "CAMEL agents not available"
        }
        
        if CAMEL_AVAILABLE:
            try:
                camel_analysis = run_camel_agents(structured_invoice)
            except Exception as e:
                logger.error(f"CAMEL agents failed: {e}", exc_info=True)
                camel_analysis = {
                    "issues": [f"Agent processing error: {str(e)}"],
                    "confidence": 0.70,
                    "notes": f"Agent processing encountered an error: {str(e)}"
                }
        else:
            logger.warning("CAMEL agents not available, using fallback validation")
            # Simple fallback validation
            camel_analysis = _simple_validation(structured_invoice)
        
        agents_latency = int((time.time() - agents_start) * 1000)
        
        # ========================================================================
        # Return Unified Response
        # ========================================================================
        return JSONResponse({
            "invoice_id": invoice_id,
            "ocr_preview": ocr_text[:3000] if len(ocr_text) > 3000 else ocr_text,  # Limit preview
            "structured_invoice": structured_invoice,
            "camel_analysis": camel_analysis,
            "latency_ms": {
                "ocr": ocr_latency,
                "llm": llm_latency,
                "agents": agents_latency
            }
        })
        
    except Exception as e:
        logger.error(f"Error processing invoice: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


def _create_fallback_invoice(ocr_text: str) -> Dict[str, Any]:
    """Create a fallback invoice structure when LLM extraction fails."""
    return {
        "document_type": "invoice",
        "vendor": {
            "name": "Unknown Vendor",
            "address": "",
            "contact": {}
        },
        "invoice_number": "",
        "invoice_date": "",
        "due_date": "",
        "line_items": [],
        "financial_summary": {
            "subtotal": 0.0,
            "tax_rate": 0.0,
            "tax_amount": 0.0,
            "grand_total": 0.0
        },
        "_fallback": True,
        "_note": "LLM extraction failed, using fallback structure"
    }


def _simple_validation(invoice: Dict[str, Any]) -> Dict[str, Any]:
    """Simple validation when CAMEL agents are not available."""
    issues = []
    confidence = 0.90
    
    # Check financial summary
    financial = invoice.get("financial_summary", {})
    subtotal = financial.get("subtotal", 0.0)
    tax_amount = financial.get("tax_amount", 0.0)
    grand_total = financial.get("grand_total", 0.0)
    
    # Check arithmetic
    expected_total = subtotal + tax_amount
    if abs(expected_total - grand_total) > 0.01:
        issues.append(f"Total mismatch: expected {expected_total:.2f}, got {grand_total:.2f}")
        confidence = 0.75
    
    # Check line items
    line_items = invoice.get("line_items", [])
    if not line_items:
        issues.append("No line items found")
        confidence = 0.80
    
    notes = "Simple validation: " + ("Issues found" if issues else "No issues detected")
    
    return {
        "issues": issues,
        "confidence": confidence,
        "notes": notes
    }

