# backend/pipeline/walmart_pipeline.py
"""
Walmart receipt processing pipeline.

End-to-end pipeline: OCR -> parse -> validation -> store stages.
"""
import uuid, time, logging
from backend.ocr.paddle_client import run_paddleocr
from backend.parsers.walmart_parser import parse_walmart_from_ocr
from backend.storage import etl as storage_etl
from backend.validation.finance_validator import validate_invoice_basic

LOG = logging.getLogger("walmart_pipeline")

def run_walmart_pipeline(image_path: str) -> dict:
    """
    Run end-to-end: OCR -> parse -> basic validation -> store stages -> return structured result.
    """
    invoice_id = str(uuid.uuid4())
    t0 = time.time()

    # 1) OCR
    ocr = run_paddleocr(image_path)
    preprocess_latency = 0  # if preprocessing added, measure; here we directly use image_path

    # 2) parse walmart-specific fields
    parsed = parse_walmart_from_ocr(ocr)

    # 3) basic validation
    try:
        validation = validate_invoice_basic(parsed)
        validation_ok = validation.get("ok", False)
    except Exception as e:
        LOG.exception("Validation failed: %s", e)
        validation = {"ok": False, "errors": [str(e)]}
        validation_ok = False

    # 4) store stages
    try:
        storage_etl.store_stage("raw_ocr", invoice_id, ocr)
        storage_etl.store_stage("parsed", invoice_id, parsed)
        storage_etl.store_stage("validated", invoice_id, {"validation": validation})
    except Exception as e:
        LOG.exception("Failed to store stages: %s", e)

    total_latency = int((time.time() - t0) * 1000)
    result = {
        "invoice_id": invoice_id,
        "structured_invoice": parsed,
        "validation": validation,
        "confidence": 1.0 if validation_ok else 0.5,
        "latency_ms": {"ocr": ocr.get("latency_ms", 0), "total": total_latency},
        "fallback_used": (ocr.get("latency_ms", 0) == 0 and ocr.get("raw_text", "").startswith("WALMART") is False)
    }
    return result

