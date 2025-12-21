"""
Mock Validator Service - Offline, deterministic validator for testing.
Provides /v1/validate endpoint that corrects invoice JSON without requiring an LLM.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)
app = FastAPI(title="Mock Validator (Offline)")

class ValidatePayload(BaseModel):
    doc_id: Optional[str] = None
    ocr_text: Optional[str] = None
    ocr_json: Optional[Dict[str, Any]] = None


def safe_parse_json(maybe) -> Optional[Dict[str, Any]]:
    """Safely parse JSON from various input types."""
    if isinstance(maybe, dict):
        return maybe
    if not maybe:
        return None
    try:
        if isinstance(maybe, str):
            return json.loads(maybe)
    except Exception:
        return None
    return None


@app.post("/v1/validate")
async def validate(payload: ValidatePayload):
    """
    Validate and correct invoice JSON.
    Accepts either OCR raw text or partially-structured JSON.
    Returns validated, corrected JSON invoice (deterministic).
    """
    ocr_json = safe_parse_json(payload.ocr_json)
    
    # If no JSON provided, try to parse from OCR text
    if ocr_json is None and payload.ocr_text:
        # Basic heuristic parse from OCR text
        lines = payload.ocr_text.splitlines()
        vendor = lines[0].strip() if lines else "Unknown Vendor"
        
        # Naive line-item extraction
        line_items = []
        for ln in lines:
            ln = ln.strip()
            if any(k in ln.lower() for k in ["qty", "unit", "total", "x", "item"]):
                # Attempt to parse like "Widget 2 x 50.00 = 100.00"
                parts = ln.replace("=", " ").replace("$", " ").replace(",", "").split()
                nums = [p for p in parts if any(c.isdigit() or c == "." for c in p)]
                
                if len(nums) >= 2:
                    try:
                        qty = int(float(nums[0]))
                        unit = float(nums[1])
                        line_total = round(qty * unit, 2)
                        desc = " ".join([p for p in parts if not any(c.isdigit() or c == "." for c in p)])
                        line_items.append({
                            "desc": desc.strip() or "item",
                            "qty": qty,
                            "unit_price": unit,
                            "line_total": line_total
                        })
                    except Exception:
                        continue
        
        subtotal = round(sum([li["line_total"] for li in line_items]), 2) if line_items else 0.0
        tax_rate = 0.10  # Default 10% tax
        tax = round(subtotal * tax_rate, 2)
        grand = round(subtotal + tax, 2)
        
        ocr_json = {
            "document_type": "invoice",
            "vendor": {"name": vendor},
            "client": {},
            "line_items": line_items,
            "financial_summary": {
                "subtotal": subtotal,
                "tax_rate": tax_rate,
                "tax_amount": tax,
                "grand_total": grand
            }
        }
    
    if ocr_json is None:
        raise HTTPException(
            status_code=400,
            detail="No ocr_json or ocr_text provided or could not parse."
        )
    
    # Validation: verify arithmetic
    line_sum = round(sum(item.get("line_total", 0.0) for item in ocr_json.get("line_items", [])), 2)
    fs = ocr_json.get("financial_summary", {})
    declared_subtotal = round(fs.get("subtotal", 0.0), 2)
    declared_g = round(fs.get("grand_total", 0.0), 2)
    tax_amount = round(fs.get("tax_amount", 0.0), 2)
    
    notes = []
    
    # Check subtotal
    if not abs(line_sum - declared_subtotal) < 0.01:
        notes.append(f"subtotal_mismatch: computed {line_sum} != declared {declared_subtotal}; adjusting.")
        fs["subtotal"] = line_sum
    
    # Check grand total
    computed_total = round(fs["subtotal"] + tax_amount, 2)
    if not abs(computed_total - declared_g) < 0.01:
        notes.append(f"grand_total_mismatch: computed {computed_total} != declared {declared_g}; adjusting.")
        fs["grand_total"] = computed_total
    
    # Ensure tax is computed if missing
    if tax_amount == 0.0 and fs.get("tax_rate", 0.0) > 0:
        tax_amount = round(fs["subtotal"] * fs["tax_rate"], 2)
        fs["tax_amount"] = tax_amount
        fs["grand_total"] = round(fs["subtotal"] + tax_amount, 2)
    
    # Finalize financial summary
    fs["subtotal"] = round(fs["subtotal"], 2)
    fs["tax_amount"] = round(fs["tax_amount"], 2)
    fs["grand_total"] = round(fs["grand_total"], 2)
    
    ocr_json["financial_summary"] = fs
    ocr_json["validation"] = {
        "arithmetic_valid": len(notes) == 0,
        "notes": notes
    }
    
    return {
        "doc_id": payload.doc_id,
        "status": "success",
        "corrected": ocr_json
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "mock_validator"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)


