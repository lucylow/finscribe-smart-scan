"""
CAMEL-AI integration endpoints for FinScribe.
Exposes /process_invoice endpoint that uses CAMEL agents to orchestrate OCR and validation.
"""
import os
import json
import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

try:
    import sys
    from pathlib import Path
    # Add project root to path for imports
    project_root = Path(__file__).parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from camel_agent import make_agent
    from camel_tools import call_ocr_file_bytes, call_validator
    CAMEL_AVAILABLE = True
except ImportError as e:
    CAMEL_AVAILABLE = False
    logging.warning(f"CAMEL-AI not available: {e}. Install with: pip install 'camel-ai[all]'")

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize agent (lazy initialization)
_agent = None


def get_agent():
    """Lazy initialization of CAMEL agent."""
    global _agent
    if _agent is None:
        if not CAMEL_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="CAMEL-AI is not installed. Install with: pip install 'camel-ai[all]'"
            )
        try:
            _agent = make_agent()
            logger.info("CAMEL agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize CAMEL agent: {e}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail=f"Failed to initialize CAMEL agent: {str(e)}"
            )
    return _agent


@router.post("/process_invoice")
async def process_invoice(
    file: UploadFile = File(...),
    doc_id: Optional[str] = None,
    use_agent: bool = True
):
    """
    Process invoice using CAMEL agent orchestration.
    
    Flow:
    1. Upload file → OCR service (via tool)
    2. OCR result → Validation service (via tool)
    3. Return corrected JSON
    
    Args:
        file: Invoice image/PDF file
        doc_id: Optional document ID for tracking
        use_agent: If True, use CAMEL agent; if False, call tools directly
        
    Returns:
        JSON with corrected invoice structure
    """
    if not CAMEL_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="CAMEL-AI is not available"
        )
    
    try:
        file_bytes = await file.read()
        
        if use_agent:
            # Use CAMEL agent to orchestrate
            agent = get_agent()
            
            # Step 1: Call OCR tool directly (binary file handling)
            logger.info(f"Calling OCR for file: {file.filename}")
            ocr_resp = call_ocr_file_bytes(file_bytes, filename=file.filename or "invoice.png")
            
            # Extract text and JSON from OCR response
            ocr_text = ocr_resp.get("text", "")
            ocr_json = ocr_resp.get("data") or ocr_resp.get("structured_data") or {}
            
            # Step 2: Ask agent to validate using tools
            user_prompt = f"""Process this invoice OCR output. 
            
OCR Text:
{ocr_text}

OCR JSON:
{json.dumps(ocr_json, indent=2) if ocr_json else '{}'}

Please validate and correct the invoice JSON structure. Use the validation tool to get the corrected JSON."""
            
            try:
                from camel.messages import BaseMessage
                prompt_msg = BaseMessage.make_user_message(content=user_prompt)
                resp = agent.step(prompt_msg)
                
                # Extract response content
                content = resp.msgs[0].content if resp.msgs else None
                
                # Try to extract JSON from agent response
                if content:
                    json_match = re.search(r"\{[\s\S]*\}", content)
                    if json_match:
                        corrected = json.loads(json_match.group(0))
                    else:
                        # Fallback: use validator tool directly
                        logger.warning("Agent response did not contain JSON, using validator tool directly")
                        val_resp = call_validator(ocr_text=ocr_text, ocr_json=ocr_json, doc_id=doc_id)
                        corrected = val_resp.get("corrected", ocr_json)
                else:
                    # No response from agent, use validator directly
                    logger.warning("Agent returned no response, using validator tool directly")
                    val_resp = call_validator(ocr_text=ocr_text, ocr_json=ocr_json, doc_id=doc_id)
                    corrected = val_resp.get("corrected", ocr_json)
            except Exception as agent_error:
                logger.warning(f"Agent step failed: {agent_error}, falling back to direct validator call")
                # Fallback to direct validator call
                val_resp = call_validator(ocr_text=ocr_text, ocr_json=ocr_json, doc_id=doc_id)
                corrected = val_resp.get("corrected", ocr_json)
        else:
            # Direct tool calls (no agent)
            logger.info("Using direct tool calls (no agent)")
            ocr_resp = call_ocr_file_bytes(file_bytes, filename=file.filename or "invoice.png")
            ocr_text = ocr_resp.get("text", "")
            ocr_json = ocr_resp.get("data") or ocr_resp.get("structured_data") or {}
            
            val_resp = call_validator(ocr_text=ocr_text, ocr_json=ocr_json, doc_id=doc_id)
            corrected = val_resp.get("corrected", ocr_json)
        
        # Save to active learning queue if enabled
        al_file = os.getenv("ACTIVE_LEARNING_FILE", "data/active_learning.jsonl")
        if al_file and os.path.dirname(al_file):
            os.makedirs(os.path.dirname(al_file), exist_ok=True)
        
        try:
            entry = {
                "prompt": ocr_text,
                "completion": corrected,
                "meta": {
                    "doc_id": doc_id,
                    "filename": file.filename,
                    "saved_at": datetime.utcnow().isoformat()
                }
            }
            with open(al_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as al_error:
            logger.warning(f"Failed to save to active learning queue: {al_error}")
        
        return JSONResponse({
            "doc_id": doc_id,
            "status": "success",
            "corrected": corrected,
            "ocr": {
                "text": ocr_text,
                "raw": ocr_resp
            }
        })
        
    except Exception as e:
        logger.error(f"Error processing invoice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/camel/health")
async def camel_health():
    """Health check for CAMEL agent service."""
    if not CAMEL_AVAILABLE:
        return JSONResponse({
            "status": "unavailable",
            "message": "CAMEL-AI is not installed"
        }, status_code=503)
    
    try:
        agent = get_agent()
        return JSONResponse({
            "status": "ok",
            "message": "CAMEL agent is available",
            "tools": len(agent.tools) if hasattr(agent, 'tools') else 0
        })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=503)

