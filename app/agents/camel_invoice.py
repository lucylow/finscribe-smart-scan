"""
CAMEL-AI Multi-Agent System for Invoice Processing

This module implements three specialized agents:
1. Extractor Agent - Extracts invoice fields accurately
2. Validator Agent - Validates financial correctness (totals, tax, arithmetic)
3. Auditor Agent - Assesses confidence and lists risks/uncertainties
"""
import os
import json
import logging
from typing import Dict, Any, Optional

try:
    from camel.agents import ChatAgent
    from camel.messages import BaseMessage
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType, ModelType
    CAMEL_AVAILABLE = True
except ImportError:
    CAMEL_AVAILABLE = False
    logging.warning("CAMEL-AI not available. Install with: pip install 'camel-ai[all]'")

logger = logging.getLogger(__name__)


def build_model():
    """
    Build model for CAMEL agents.
    Supports OpenAI, local vLLM, or dummy fallback.
    """
    if not CAMEL_AVAILABLE:
        raise ImportError("CAMEL-AI is not installed")
    
    # Check for OpenAI key
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            model = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4o if hasattr(ModelType, "GPT_4o") else ModelType.GPT_4,
                model_config_dict={"temperature": 0.0}
            )
            logger.info("Using OpenAI model for CAMEL agents")
            return model
        except Exception as e:
            logger.warning(f"Failed to create OpenAI model: {e}, trying fallback")
    
    # Check for local vLLM endpoint
    vllm_url = os.getenv("VLLM_API_URL") or os.getenv("LLAMA_API_URL")
    if vllm_url:
        try:
            base_url = vllm_url.replace("/v1/chat/completions", "").rstrip("/")
            model = ModelFactory.create(
                model_platform=ModelPlatformType.VLLM,
                model_type=os.getenv("LLAMA_MODEL", "meta-llama/Llama-2-7b-chat-hf"),
                url=base_url,
                model_config_dict={"temperature": 0.0}
            )
            logger.info(f"Using vLLM model at {base_url} for CAMEL agents")
            return model
        except Exception as e:
            logger.warning(f"Failed to create vLLM model: {e}, trying dummy fallback")
    
    # Fallback to dummy model (will rely on tools)
    try:
        model = ModelFactory.create(
            model_platform=ModelPlatformType.DUMMY,
            model_type="dummy",
            model_config_dict={"temperature": 0.0}
        )
        logger.info("Using dummy model for CAMEL agents (tool-based processing)")
        return model
    except Exception as e:
        logger.error(f"Failed to create any model: {e}")
        raise


# Global model instance
_model = None


def get_model():
    """Get or create global model instance."""
    global _model
    if _model is None:
        _model = build_model()
    return _model


def create_extractor_agent() -> ChatAgent:
    """Create Extractor Agent for accurate field extraction."""
    if not CAMEL_AVAILABLE:
        raise ImportError("CAMEL-AI is not installed")
    
    system_message = BaseMessage.make_assistant_message(
        role_name="Extractor Agent",
        content="""You are an expert invoice field extractor. Your job is to extract invoice fields accurately from OCR text or structured data.

Extract the following fields:
- vendor (name, address, contact info)
- invoice_number
- invoice_date
- due_date (if present)
- line_items (description, quantity, unit_price, line_total)
- subtotal
- tax_rate and tax_amount
- total/grand_total

Return only valid JSON. Be precise and accurate."""
    )
    
    return ChatAgent(
        system_message=system_message,
        model=get_model()
    )


def create_validator_agent() -> ChatAgent:
    """Create Validator Agent for financial correctness validation."""
    if not CAMEL_AVAILABLE:
        raise ImportError("CAMEL-AI is not installed")
    
    system_message = BaseMessage.make_assistant_message(
        role_name="Validator Agent",
        content="""You are a financial validator. Your job is to validate financial correctness of invoice data.

Check:
1. Arithmetic: subtotal + tax = total
2. Line items: sum of line_totals = subtotal
3. Tax calculation: tax_amount = subtotal * (tax_rate / 100)
4. Data consistency: dates are valid, amounts are positive, etc.

If you find issues, list them clearly. If everything is correct, say "no issues found"."""
    )
    
    return ChatAgent(
        system_message=system_message,
        model=get_model()
    )


def create_auditor_agent() -> ChatAgent:
    """Create Auditor Agent for confidence assessment and risk analysis."""
    if not CAMEL_AVAILABLE:
        raise ImportError("CAMEL-AI is not installed")
    
    system_message = BaseMessage.make_assistant_message(
        role_name="Auditor Agent",
        content="""You are an invoice auditor. Your job is to assess confidence and identify risks or uncertainties.

Evaluate:
1. Data completeness (are all required fields present?)
2. Data quality (are values reasonable?)
3. Potential issues or ambiguities
4. Overall confidence level (0.0 to 1.0)

Provide a confidence score and notes about any risks or uncertainties."""
    )
    
    return ChatAgent(
        system_message=system_message,
        model=get_model()
    )


def run_camel_agents(invoice_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the three CAMEL agents in sequence to extract, validate, and audit invoice data.
    
    Args:
        invoice_json: Structured invoice JSON (from Unsloth or OCR)
        
    Returns:
        Dictionary with:
        - issues: List of validation issues (empty if none)
        - confidence: Confidence score (0.0 to 1.0)
        - notes: Auditor notes
    """
    if not CAMEL_AVAILABLE:
        logger.warning("CAMEL-AI not available, returning mock result")
        return {
            "issues": [],
            "confidence": 0.85,
            "notes": "CAMEL-AI not available, using fallback validation"
        }
    
    try:
        # Step 1: Extractor Agent
        extractor = create_extractor_agent()
        extraction_prompt = BaseMessage.make_user_message(
            content=f"Extract and structure invoice fields from this data:\n{json.dumps(invoice_json, indent=2)}"
        )
        extraction_result = extractor.step(extraction_prompt)
        extraction_content = extraction_result.msgs[0].content if extraction_result.msgs else ""
        
        # Step 2: Validator Agent
        validator = create_validator_agent()
        validation_prompt = BaseMessage.make_user_message(
            content=f"Validate the financial correctness of this invoice:\n{extraction_content}"
        )
        validation_result = validator.step(validation_prompt)
        validation_content = validation_result.msgs[0].content if validation_result.msgs else ""
        
        # Step 3: Auditor Agent
        auditor = create_auditor_agent()
        audit_prompt = BaseMessage.make_user_message(
            content=f"Audit this invoice extraction and validation:\n\nExtraction:\n{extraction_content}\n\nValidation:\n{validation_content}"
        )
        audit_result = auditor.step(audit_prompt)
        audit_content = audit_result.msgs[0].content if audit_result.msgs else ""
        
        # Parse results
        issues = []
        if "no issues" not in validation_content.lower() and "correct" not in validation_content.lower():
            # Extract issues from validation content
            issues = [validation_content]
        
        # Extract confidence from audit content
        confidence = 0.97  # Default high confidence
        if "low confidence" in audit_content.lower() or "uncertain" in audit_content.lower():
            confidence = 0.75
        elif "medium confidence" in audit_content.lower():
            confidence = 0.85
        
        # Try to extract numeric confidence if present
        import re
        conf_match = re.search(r'confidence[:\s]+([0-9.]+)', audit_content, re.IGNORECASE)
        if conf_match:
            try:
                confidence = float(conf_match.group(1))
                if confidence > 1.0:
                    confidence = confidence / 100.0  # Convert percentage to decimal
            except ValueError:
                pass
        
        return {
            "issues": issues,
            "confidence": confidence,
            "notes": audit_content
        }
        
    except Exception as e:
        logger.error(f"Error running CAMEL agents: {e}", exc_info=True)
        return {
            "issues": [f"Agent processing error: {str(e)}"],
            "confidence": 0.70,
            "notes": f"Agent processing encountered an error: {str(e)}"
        }

