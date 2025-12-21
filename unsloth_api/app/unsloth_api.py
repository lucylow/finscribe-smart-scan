"""
Standalone Unsloth API Service

FastAPI service for Unsloth inference. Can be run as a separate microservice
or integrated into the main FinScribe backend.
"""
import os
import json
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
import torch

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


@app.post("/v1/infer", response_model=UnslothResponse)
async def infer(payload: OCRPayload):
    """Run Unsloth inference on OCR text."""
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
            model_available=False
        )
    
    try:
        # Build prompt
        instruction = payload.instruction or (
            "\n\nExtract structured JSON with vendor, invoice_number, dates, "
            "line_items, and financial_summary. Output only valid JSON."
        )
        prompt = f"OCR_TEXT:\n{payload.ocr_text}{instruction}"
        
        # Tokenize
        inputs = tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=2048
        ).to(device)
        
        # Generate
        gen_config = GenerationConfig(
            temperature=payload.temperature,
            top_p=0.95,
            do_sample=(payload.temperature > 0.0),
            max_new_tokens=payload.max_new_tokens or 512,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )
        
        with torch.no_grad():
            outputs = model.generate(**inputs, generation_config=gen_config)
        
        # Decode
        decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract JSON
        parsed = extract_json(decoded, len(prompt))
        
        return UnslothResponse(
            doc_id=payload.doc_id,
            parsed=parsed,
            model_available=True
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


