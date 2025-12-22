"""
Standalone Unsloth API Service

FastAPI service for Unsloth inference. Can be run as a separate microservice
or integrated into the main FinScribe backend.
"""
import os
import json
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
import torch

# Import prompt templates and semantic filtering
try:
    from .prompt_templates import build_few_shot_prompt, build_zero_shot_prompt
    PROMPT_TEMPLATES_AVAILABLE = True
except ImportError:
    PROMPT_TEMPLATES_AVAILABLE = False
    logger.warning("Prompt templates not available, using default prompts")

# Import semantic block filtering
try:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'ocr'))
    from paddle_wrapper import get_structured_ocr_output
    SEMANTIC_FILTERING_AVAILABLE = True
except ImportError:
    SEMANTIC_FILTERING_AVAILABLE = False
    logger.warning("Semantic filtering not available")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Unsloth FinScribe API",
    description="Unsloth inference service for structured JSON extraction from OCR text",
    version="1.0.0"
)

# Configuration
MODEL_DIR = os.environ.get("MODEL_DIR", "/models/unsloth-finscribe")
device = "cuda" if torch.cuda.is_available() else "cpu"

# Global model variables
tokenizer = None
model = None


def load_model():
    """Load tokenizer and model."""
    global tokenizer, model
    try:
        logger.info(f"Loading Unsloth model from {MODEL_DIR}")
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_DIR, use_fast=True, trust_remote_code=True
        )
        
        dtype = torch.float16 if device == "cuda" else torch.float32
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_DIR,
            torch_dtype=dtype,
            trust_remote_code=True,
        ).to(device)
        
        model.eval()
        logger.info(f"Model loaded successfully on {device}")
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}", exc_info=True)
        logger.warning("Model not loaded - will return mock responses")


# Load model on startup
@app.on_event("startup")
async def startup_event():
    """Load model when API starts."""
    if os.path.exists(MODEL_DIR):
        load_model()
    else:
        logger.warning(f"Model directory {MODEL_DIR} does not exist - running in mock mode")


# Request/Response models
class OCRPayload(BaseModel):
    doc_id: Optional[str] = None
    ocr_text: str
    instruction: Optional[str] = None
    max_new_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.0


class UnslothResponse(BaseModel):
    doc_id: Optional[str] = None
    parsed: dict
    model_available: bool
    confidence_score: Optional[float] = None
    needs_review: Optional[bool] = None


def extract_json(decoded_text: str, prompt_length: int) -> dict:
    """Extract JSON from model output."""
    try:
        json_start = decoded_text.find("{", prompt_length)
        if json_start == -1:
            json_start = decoded_text.find("{")
        
        if json_start != -1:
            json_text = decoded_text[json_start:]
            return json.loads(json_text)
        else:
            return {"_raw_output": decoded_text, "_parse_error": True}
    except json.JSONDecodeError as e:
        try:
            import re
            json_match = re.search(r'\{.*\}', decoded_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        return {"_raw_output": decoded_text, "_parse_error": True, "_error": str(e)}


def calculate_hybrid_confidence(
    parsed: Dict[str, Any],
    ocr_result: Optional[Dict[str, Any]] = None,
    validation_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculate hybrid confidence score combining multiple factors.
    
    Factors:
    1. OCR Confidence: Average confidence of bounding boxes used
    2. LLM Adherence: How well output adheres to JSON schema
    3. Validation Agent Score: Arithmetic/business rule validation
    
    Returns:
        Dict with confidence_score (0-1) and needs_review (bool)
    """
    scores = []
    weights = []
    
    # Factor 1: OCR Confidence (if available)
    if ocr_result:
        regions = ocr_result.get("regions", [])
        if regions:
            ocr_confidences = [r.get("confidence", 0.0) for r in regions if isinstance(r, dict)]
            if ocr_confidences:
                ocr_avg = sum(ocr_confidences) / len(ocr_confidences)
                scores.append(ocr_avg)
                weights.append(0.3)  # 30% weight
                logger.debug(f"OCR confidence: {ocr_avg:.3f}")
    
    # Factor 2: LLM Adherence (JSON parsing success)
    llm_adherence = 1.0
    if parsed.get("_parse_error"):
        llm_adherence = 0.0
    elif parsed.get("_raw_output"):
        # Partial parsing - lower score
        llm_adherence = 0.5
    else:
        # Check if required fields are present
        required_fields = ["document_type", "financial_summary"]
        present_fields = sum(1 for field in required_fields if field in parsed)
        llm_adherence = present_fields / len(required_fields)
    
    scores.append(llm_adherence)
    weights.append(0.4)  # 40% weight
    logger.debug(f"LLM adherence: {llm_adherence:.3f}")
    
    # Factor 3: Validation Agent Score
    validation_score = 1.0
    if validation_result:
        if validation_result.get("is_valid", False):
            validation_score = 1.0
        elif validation_result.get("math_ok", True):  # Soft warning
            validation_score = 0.5
        else:  # Hard fail
            validation_score = 0.0
    else:
        # Perform basic arithmetic validation if validation_result not provided
        validation_score = _validate_arithmetic_basic(parsed)
    
    scores.append(validation_score)
    weights.append(0.3)  # 30% weight
    logger.debug(f"Validation score: {validation_score:.3f}")
    
    # Calculate weighted average
    if len(scores) > 0 and len(weights) > 0:
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            normalized_weights = [w / total_weight for w in weights]
            hybrid_score = sum(s * w for s, w in zip(scores, normalized_weights))
        else:
            hybrid_score = sum(scores) / len(scores) if scores else 0.5
    else:
        hybrid_score = 0.5  # Default if no scores
    
    # Flag for human review if score is below threshold
    needs_review = hybrid_score < 0.90
    
    return {
        "confidence_score": hybrid_score,
        "needs_review": needs_review,
        "component_scores": {
            "ocr_confidence": scores[0] if len(scores) > 0 else None,
            "llm_adherence": scores[1] if len(scores) > 1 else None,
            "validation_score": scores[2] if len(scores) > 2 else None
        }
    }


def _validate_arithmetic_basic(parsed: Dict[str, Any], tolerance: float = 0.01) -> float:
    """
    Basic arithmetic validation (fallback if validation service not available).
    
    Returns:
        Score: 1.0 for pass, 0.5 for soft warning, 0.0 for hard fail
    """
    try:
        fs = parsed.get("financial_summary", {})
        if not fs:
            return 0.5  # Missing financial summary
        
        subtotal = fs.get("subtotal", 0.0) or 0.0
        tax = fs.get("tax", 0.0) or 0.0
        grand_total = fs.get("grand_total", 0.0) or 0.0
        
        if grand_total == 0:
            return 0.5  # Missing grand total
        
        # Check: subtotal + tax ≈ grand_total
        expected_total = subtotal + tax
        difference = abs(expected_total - grand_total)
        
        if difference < tolerance:
            return 1.0  # Perfect match
        elif difference < 1.0:  # Small difference (soft warning)
            return 0.5
        else:  # Large difference (hard fail)
            return 0.0
    except Exception as e:
        logger.warning(f"Arithmetic validation failed: {e}")
        return 0.5  # Default to medium confidence on error


@app.post("/v1/infer", response_model=UnslothResponse)
async def infer(payload: OCRPayload):
    """Run Unsloth inference on OCR text with enhanced prompting and confidence scoring."""
    if model is None or tokenizer is None:
        # Return mock response
        return UnslothResponse(
            doc_id=payload.doc_id,
            parsed={
                "document_type": "invoice",
                "vendor": {"name": "Mock Vendor"},
                "line_items": [],
                "financial_summary": {"subtotal": 0.0, "grand_total": 0.0},
                "_mock": True
            },
            model_available=False,
            confidence_score=0.5,
            needs_review=True
        )
    
    try:
        # Step 1: Apply semantic block filtering if OCR result is structured
        structured_ocr_text = payload.ocr_text
        ocr_result = None
        
        # Try to parse OCR text as structured result
        try:
            if payload.ocr_text.startswith("{") or "regions" in payload.ocr_text.lower():
                # Might be JSON-structured OCR result
                ocr_result = json.loads(payload.ocr_text) if payload.ocr_text.startswith("{") else None
                if ocr_result and SEMANTIC_FILTERING_AVAILABLE:
                    structured_ocr_text = get_structured_ocr_output(ocr_result)
                    logger.info("Applied semantic block filtering to OCR output")
        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"OCR text is not structured JSON, using as-is: {e}")
        
        # Step 2: Build prompt using few-shot template
        if PROMPT_TEMPLATES_AVAILABLE:
            try:
                prompt = build_few_shot_prompt(structured_ocr_text)
                logger.debug("Using few-shot prompt template")
            except Exception as e:
                logger.warning(f"Few-shot prompt failed, using zero-shot: {e}")
                prompt = build_zero_shot_prompt(structured_ocr_text)
        else:
            # Fallback to simple prompt
            instruction = payload.instruction or (
                "\n\nExtract structured JSON with vendor, invoice_number, dates, "
                "line_items, and financial_summary. Output only valid JSON."
            )
            prompt = f"OCR_TEXT:\n{structured_ocr_text}{instruction}"
        
        # Step 3: Tokenize and generate
        inputs = tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=2048
        ).to(device)
        
        gen_config = GenerationConfig(
            temperature=payload.temperature,
            top_p=0.95,
            do_sample=(payload.temperature > 0.0),
            max_new_tokens=payload.max_new_tokens or 512,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )
        
        with torch.no_grad():
            outputs = model.generate(**inputs, generation_config=gen_config)
        
        # Step 4: Decode and extract JSON
        decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
        parsed = extract_json(decoded, len(prompt))
        
        # Step 5: Perform validation (basic arithmetic check)
        validation_result = None
        try:
            validation_result = {
                "is_valid": not parsed.get("_parse_error", False),
                "math_ok": _validate_arithmetic_basic(parsed) >= 0.5
            }
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
        
        # Step 6: Calculate hybrid confidence score
        confidence_data = calculate_hybrid_confidence(
            parsed,
            ocr_result=ocr_result,
            validation_result=validation_result
        )
        
        return UnslothResponse(
            doc_id=payload.doc_id,
            parsed=parsed,
            model_available=True,
            confidence_score=confidence_data["confidence_score"],
            needs_review=confidence_data["needs_review"]
        )
        
    except Exception as e:
        logger.error(f"Inference error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model_available": model is not None,
        "device": device,
        "model_dir": MODEL_DIR
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


