# backend/pipeline/ocr_pipeline.py
from backend.ocr.paddle_client import run_paddleocr
from backend.parsers.simple_parser import parse_basic  # create simple parser or reuse existing
from backend.llm.ernie_client import call_ernie_validate  # optional
import time, uuid, logging

LOG = logging.getLogger("ocr_pipeline")

def run_full_pipeline(image_path: str, use_ernie: bool = False) -> dict:
    t0 = time.time()
    ocr = run_paddleocr(image_path)
    parsed = parse_basic(ocr)  # basic rule-based parser
    validation = {"ok": False, "errors": []}
    fallback_used = False
    if use_ernie:
        try:
            ernie_res = call_ernie_validate(parsed, ocr.get("raw_text",""))
            parsed = ernie_res.get("validated_invoice", parsed)
            validation = ernie_res.get("validation", validation)
        except Exception:
            fallback_used = True
            # run simple validator (create or reuse)
            from backend.validation.finance_validator import validate_invoice_basic
            validation = validate_invoice_basic(parsed)
    else:
        from backend.validation.finance_validator import validate_invoice_basic
        validation = validate_invoice_basic(parsed)
    result = {
        "invoice_id": uuid.uuid4().hex,
        "structured_invoice": parsed,
        "validation": validation,
        "confidence": 1.0 if validation.get("ok") else 0.5,
        "latency_ms": {"ocr": ocr.get("latency_ms",0), "total": int((time.time()-t0)*1000)},
        "fallback_used": fallback_used
    }
    return result

