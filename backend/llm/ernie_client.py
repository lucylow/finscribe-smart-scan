# backend/llm/ernie_client.py
import os, time, logging, json, requests
from backend.utils.safe_json import safe_json_parse
from backend.validation.finance_validator import validate_invoice_basic

LOG = logging.getLogger("ernie_client")
ERNIE_URL = os.getenv("ERNIE_URL", "").strip()
MAX_RETRIES = int(os.getenv("ERNIE_RETRIES", "2"))

PROMPT_TEMPLATE = """
You are ERNIE: given OCR text and a draft invoice JSON, return strict JSON ONLY in this format:
{{"validated_invoice": {{...}}, "validation": {{ "ok": bool, "errors": [] }}, "field_confidences": {{}} }}
OCR_TEXT:
{ocr}
DRAFT_JSON:
{draft}
"""

def call_ernie_validate(draft: dict, ocr_text: str, timeout: int = 15) -> dict:
    if not ERNIE_URL:
        LOG.info("ERNIE_URL not set - returning mock validation")
        return _mock_response(draft)
    payload = {"prompt": PROMPT_TEMPLATE.format(ocr=ocr_text, draft=json.dumps(draft, default=str))}
    for attempt in range(MAX_RETRIES+1):
        try:
            t0 = time.time()
            r = requests.post(ERNIE_URL, json=payload, timeout=timeout)
            r.raise_for_status()
            txt = r.text
            parsed = safe_json_parse(txt)
            parsed["latency_ms"] = int((time.time()-t0)*1000)
            return parsed
        except Exception as e:
            LOG.exception("Ernie call failed attempt=%s: %s", attempt, e)
    LOG.warning("All ERNIE attempts failed - using local validator")
    return _mock_response(draft)

def _mock_response(draft: dict) -> dict:
    validation = validate_invoice_basic(draft)
    return {"validated_invoice": draft, "validation": validation, "field_confidences": {}, "latency_ms": 0}
