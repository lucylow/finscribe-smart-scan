# backend/pipeline/ocr_pipeline.py
import time, uuid, logging
from backend.ocr.paddle_client import run_paddleocr
from backend.parsers.simple_parser import parse_basic
from backend.storage.storage import save_job_result, save_job_status
from backend.llm.ernie_client import call_ernie_validate

LOG = logging.getLogger("ocr_pipeline")

def run_full_pipeline(image_path: str, use_ernie: bool = True) -> dict:
    invoice_id = str(uuid.uuid4())
    t0 = time.time()
    save_job_status(invoice_id, {"status":"running", "ts": time.time()})
    ocr = run_paddleocr(image_path)
    parsed = parse_basic(ocr)
    validation = {"ok": False, "errors": ["not validated"]}
    ernie_latency = 0
    fallback_used = False
    if use_ernie:
        try:
            ernie_res = call_ernie_validate(parsed, ocr.get("raw_text",""))
            validation = ernie_res.get("validation", validation)
            parsed = ernie_res.get("validated_invoice", parsed)
            ernie_latency = ernie_res.get("latency_ms", 0)
        except Exception:
            LOG.exception("Ernie validation failed, falling back to local validate")
            fallback_used = True
            # simple local validation
            from backend.validation.finance_validator import validate_invoice_basic
            validation = validate_invoice_basic(parsed)
    else:
        from backend.validation.finance_validator import validate_invoice_basic
        validation = validate_invoice_basic(parsed)

    total_latency = int((time.time()-t0)*1000)
    result = {
        "invoice_id": invoice_id,
        "paddle": {"raw_text": ocr.get("raw_text"), "words": ocr.get("words", []), "latency_ms": ocr.get("latency_ms",0), "model": ocr.get("model","unknown")},
        "structured_invoice": parsed,
        "validation": validation,
        "confidence": 1.0 if validation.get("ok") else 0.5,
        "latency_ms": {"ernie": ernie_latency, "total": total_latency},
        "fallback_used": fallback_used
    }
    save_job_result(invoice_id, result)
    save_job_status(invoice_id, {"status":"done", "ts": time.time()})
    return result

