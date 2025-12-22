"""
semantic_parse_task.py

Consume OCR artifacts (JSON saved by ocr_task) and produce structured JSON for invoices.

This implements:
- heuristic/regex-based extraction of invoice fields (invoice_no, date, vendor, totals)
- simple line-item recovery by clustering OCR text boxes by Y coordinate and parsing numeric columns
- arithmetic validation (subtotal + tax +/- tolerance == total)
- saving structured artifact to storage (LocalStorage / MinIO)
- appending flagged examples to active_learning.jsonl for later human review / SFT

Drop into `finscribe/` and import in your worker orchestration.
Requires: python-dateutil (pip install python-dateutil)
"""

import os
import re
import json
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import List, Dict, Any, Tuple, Optional
from dateutil import parser as dateparser  # pip install python-dateutil
from datetime import datetime

from .staging import LocalStorage, read_bytes_from_storage, StorageInterface

from .celery_app import celery_app

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configure storage (replace with DI if desired)
STORAGE_BASE = os.getenv("STORAGE_BASE", "./storage")
ACTIVE_LEARNING_KEY = os.getenv("ACTIVE_LEARNING_KEY", "active_learning/active_learning.jsonl")
storage: StorageInterface = LocalStorage(STORAGE_BASE)


# ---------- Utility helpers ----------
AMOUNT_RE = re.compile(r"([£$€]?)[\s]*(-?\d{1,3}(?:[,\d{3}]*)(?:\.\d{1,4})?)")
INVOICE_NO_RE = re.compile(r"(invoice\s*#?\s*[:\-]?\s*([A-Za-z0-9\-\/]+))", re.IGNORECASE)
DATE_RE = re.compile(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})")
TOTAL_KEYWORDS = re.compile(r"\b(total|amount due|grand total|balance due)\b", re.IGNORECASE)
SUBTOTAL_KEYWORDS = re.compile(r"\b(subtotal)\b", re.IGNORECASE)
TAX_KEYWORDS = re.compile(r"\b(tax|vat)\b", re.IGNORECASE)


def _normalize_amount_text(text: str) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Extract first recognized monetary amount from text and return (Decimal, currency_symbol).
    Returns (None, None) if not found / parse fails.
    """
    if text is None:
        return None, None
    m = AMOUNT_RE.search(text.replace(",", ""))
    if not m:
        return None, None
    currency, num = m.group(1) or "", m.group(2)
    try:
        # Decimal parsing for accuracy
        dec = Decimal(num)
        # round to 2 decimal places for typical currencies
        dec = dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return dec, currency or None
    except (InvalidOperation, TypeError):
        return None, None


def _parse_date_text(text: str) -> Optional[str]:
    """Try to parse a date-like string and return ISO date or None."""
    if not text:
        return None
    m = DATE_RE.search(text)
    candidate = m.group(0) if m else text
    try:
        dt = dateparser.parse(candidate, dayfirst=False, yearfirst=False)
        return dt.date().isoformat()
    except Exception:
        return None


def _group_regions_to_rows(regions: List[Dict], y_tol: int = 10) -> List[List[Dict]]:
    """
    Cluster OCR regions into rows by their bbox Y coordinate.
    regions: list of {"text":..., "bbox":[x,y,w,h], "confidence":...}
    Returns list-of-rows; each row is a list of regions sorted by x.
    """
    # Each region center y
    items = []
    for r in regions:
        x, y, w, h = r.get("bbox", [0, 0, 0, 0])
        cy = int(y + (h / 2))
        items.append((cy, x, r))
    # sort by cy then x
    items.sort(key=lambda t: (t[0], t[1]))
    rows: List[List[Dict]] = []
    for cy, x, r in items:
        if not rows:
            rows.append([r])
        else:
            last_row_center = int(rows[-1][0].get("bbox", [0, 0, 0, 0])[1] + (rows[-1][0].get("bbox", [0, 0, 0, 0])[3] / 2))
            # compute representative center of previous row
            prev_cys = [int(rr["bbox"][1] + (rr["bbox"][3] / 2)) for rr in rows[-1]]
            prev_avg_cy = sum(prev_cys) / len(prev_cys)
            if abs(cy - prev_avg_cy) <= y_tol:
                rows[-1].append(r)
            else:
                rows.append([r])
    # sort regions in each row by x ascending
    for row in rows:
        row.sort(key=lambda r: r.get("bbox", [0, 0, 0, 0])[0])
    return rows


def _parse_line_item_row(row: List[Dict]) -> Optional[Dict]:
    """
    Heuristic to parse a line-item row: look for description text and at least one numeric amount.
    Returns a dict with desc, qty, unit_price, line_total when possible.
    """
    texts = [r.get("text", "").strip() for r in row if r.get("text")]
    joined = "  |  ".join(texts)
    # try to find all amounts in row
    amounts = []
    for r in row:
        a, _ = _normalize_amount_text(r.get("text", ""))
        if a is not None:
            amounts.append((r, a))
    if not texts:
        return None

    # if at least one numeric present, assume it's a line item
    if amounts:
        # pick last amount as line_total often
        line_total = amounts[-1][1]
        # attempt to find qty and unit price heuristically: look for small integers before amounts
        qty = None
        unit_price = None
        # naive search for integers in the row texts
        for t in texts:
            m = re.search(r"\b(\d+)\b", t)
            if m:
                qcand = m.group(1)
                try:
                    if int(qcand) > 0 and (qty is None):
                        qty = int(qcand)
                except Exception:
                    pass
        # if qty and line_total known, estimate unit_price
        if qty and line_total:
            try:
                unit_price = (line_total / Decimal(qty)).quantize(Decimal("0.01"))
            except Exception:
                unit_price = None

        # description is first text piece that is not purely numerical
        desc = None
        for t in texts:
            if not re.fullmatch(r"[-\d\.,\s\$\£\€]+", t):
                desc = t
                break
        if desc is None:
            desc = texts[0] if texts else ""

        return {
            "description": desc,
            "qty": qty,
            "unit_price": float(unit_price) if unit_price is not None else None,
            "line_total": float(line_total) if line_total is not None else None,
            "raw_text": joined,
            "confidence": min((r.get("confidence", 1.0) for r in row), default=1.0),
        }
    return None


def _extract_invoice_fields_from_regions(regions: List[Dict]) -> Dict[str, Any]:
    """
    Search through OCR regions to extract high-level invoice fields with regex heuristics.
    """
    invoice_no = None
    invoice_date = None
    vendor = None
    subtotal = None
    tax = None
    total = None
    currency = None

    # Search for invoice number/date/vendor keywords in top regions (by y)
    # sort by y (top-first)
    regions_sorted = sorted(regions, key=lambda r: r.get("bbox", [0, 0, 0, 0])[1])
    for r in regions_sorted[:30]:  # look at top ~30 regions heuristically
        txt = r.get("text", "")
        if not invoice_no:
            m = INVOICE_NO_RE.search(txt)
            if m:
                invoice_no = m.group(2)
        if not invoice_date:
            d = _parse_date_text(txt)
            if d:
                invoice_date = d
        # vendor heuristic: likely top-left block; capture a few words
    # vendor guess: combine text in left-most top area
    left_top = [r for r in regions_sorted if r.get("bbox", [0, 0, 0, 0])[0] < 300][:8]
    vendor_texts = [r.get("text", "").strip() for r in left_top]
    vendor = " ".join([t for t in vendor_texts if t]) if vendor_texts else None

    # scan for totals by searching keywords and amounts across all regions
    for r in regions:
        txt = r.get("text", "")
        a, cur = _normalize_amount_text(txt)
        if a is not None:
            if TOTAL_KEYWORDS.search(txt):
                total = a
                currency = currency or cur
            elif SUBTOTAL_KEYWORDS.search(txt):
                subtotal = a
                currency = currency or cur
            elif TAX_KEYWORDS.search(txt):
                tax = a
                currency = currency or cur

    # fallback: if no explicit total found, take largest amount found near bottom-right
    if total is None:
        # find candidate amounts and pick max and bottommost/rightmost heuristically
        cand = []
        for r in regions:
            a, cur = _normalize_amount_text(r.get("text", ""))
            if a is not None:
                x, y, w, h = r.get("bbox", [0, 0, 0, 0])
                cand.append((a, cur, x, y))
        if cand:
            # prefer the largest numeric value
            cand.sort(key=lambda t: (t[0], -t[3]), reverse=True)
            total, currency = cand[0][0], cand[0][1]

    return {
        "invoice_no": invoice_no,
        "invoice_date": invoice_date,
        "vendor": vendor,
        "subtotal": float(subtotal) if subtotal is not None else None,
        "tax": float(tax) if tax is not None else None,
        "total": float(total) if total is not None else None,
        "currency": currency,
    }


def validate_financials(structured: Dict[str, Any], tolerance: Decimal = Decimal("0.02")) -> Dict[str, Any]:
    """
    Validate arithmetic consistency: sum(line_totals) ~ subtotal; subtotal + tax ~= total.
    Returns validation dict with math_ok bool and list of errors.
    tolerance is relative (percentage), default 2%.
    """
    errors = []
    try:
        line_items = structured.get("line_items", [])
        sum_lines = Decimal("0.00")
        for li in line_items:
            lt = li.get("line_total")
            if lt is None:
                continue
            sum_lines += Decimal(str(lt))
        subtotal = structured.get("subtotal")
        tax = structured.get("tax") or 0
        total = structured.get("total")
        # Compare sums with tolerance
        math_ok = True
        if subtotal is not None:
            subtotal_dec = Decimal(str(subtotal))
            if subtotal_dec == Decimal("0"):
                # if subtotal is zero, special handling
                if sum_lines != subtotal_dec:
                    math_ok = False
                    errors.append({"code": "SUBTOTAL_MISMATCH", "calc": float(sum_lines), "declared": float(subtotal_dec)})
            else:
                diff = abs(sum_lines - subtotal_dec)
                if (diff / (subtotal_dec if subtotal_dec != 0 else Decimal("1"))) > tolerance:
                    math_ok = False
                    errors.append({"code": "SUBTOTAL_MISMATCH", "calc": float(sum_lines), "declared": float(subtotal_dec)})

        if total is not None and subtotal is not None:
            total_dec = Decimal(str(total))
            subtotal_dec = Decimal(str(subtotal))
            expected = subtotal_dec + Decimal(str(tax))
            diff2 = abs(expected - total_dec)
            if subtotal_dec == 0:
                if diff2 > Decimal("0.01"):
                    math_ok = False
                    errors.append({"code": "TOTAL_MISMATCH", "expected": float(expected), "declared": float(total_dec)})
            else:
                if (diff2 / (total_dec if total_dec != 0 else Decimal("1"))) > tolerance:
                    math_ok = False
                    errors.append({"code": "TOTAL_MISMATCH", "expected": float(expected), "declared": float(total_dec)})
        return {"math_ok": math_ok, "errors": errors}
    except Exception as e:
        logger.exception("Validation error: %s", e)
        return {"math_ok": False, "errors": [{"code": "VALIDATION_ERROR", "message": str(e)}]}


def _append_to_active_learning(record: Dict[str, Any]):
    """
    Append a JSONL record to active learning file in storage.
    """
    try:
        line = json.dumps(record, ensure_ascii=False)
        # read current file if exists
        try:
            existing = storage.get_bytes(ACTIVE_LEARNING_KEY)
            # Append newline if not endswith
            content = existing.decode("utf-8") + "\n" + line
        except Exception:
            # not exists or error: create new
            content = line
        storage.put_bytes(ACTIVE_LEARNING_KEY, content.encode("utf-8"))
        logger.info("Appended example to active learning queue: %s", ACTIVE_LEARNING_KEY)
    except Exception:
        logger.exception("Failed to append to active learning.")


# ---------- Main parse function ----------
def parse_ocr_artifact_to_structured(ocr_artifact: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert OCR artifact structure into a structured invoice JSON.
    OCR artifact expected format:
    {
      "job_id": "...",
      "page_key": "...",
      "ocr": [ {"text": "...", "bbox":[x,y,w,h], "confidence": 0.95}, ... ]
    }
    """
    regions = ocr_artifact.get("ocr", [])
    structured = _extract_invoice_fields_from_regions(regions)

    # reconstruct line items by grouping by y coordinate (rows) on the whole page
    rows = _group_regions_to_rows(regions, y_tol=12)
    line_items = []
    for row in rows:
        li = _parse_line_item_row(row)
        if li:
            line_items.append(li)

    structured["line_items"] = line_items

    # Validation (math)
    validation = validate_financials(structured, tolerance=Decimal("0.02"))
    structured["validation"] = validation
    structured["provenance"] = {
        "model_version": os.getenv("MODEL_VERSION", "paddleocr-base"),
        "parsed_at": datetime.utcnow().isoformat() + "Z",
        "source_page_key": ocr_artifact.get("page_key"),
    }
    # Add low-confidence flag if many regions low-conf
    confidences = [r.get("confidence", 1.0) for r in regions if "confidence" in r]
    avg_conf = float(sum(confidences) / len(confidences)) if confidences else 1.0
    structured["confidence_score"] = avg_conf
    structured["needs_review"] = (not validation.get("math_ok")) or (avg_conf < 0.6)

    # attach raw OCR snippet for auditing
    structured["raw_ocr_snippet"] = [{"text": r.get("text"), "bbox": r.get("bbox"), "confidence": r.get("confidence")} for r in regions[:40]]

    return structured


# ---------- Celery Task ----------
@celery_app.task(bind=True, max_retries=2, default_retry_delay=5)
def semantic_parse_task(self, job_id: str, page_key: str, ocr_artifact_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Celery task: load OCR artifact, parse into structured JSON and save result artifact.
    Args:
        job_id: job identifier
        page_key: staging page key (e.g. staging/{job_id}/page_0.png)
        ocr_artifact_key: optional explicit artifact key (e.g. ocr/{job_id}/page_0.png.json)
    """
    logger.info("semantic_parse_task start job=%s page=%s", job_id, page_key)
    try:
        if ocr_artifact_key is None:
            # infer expected artifact key
            basename = page_key.split("/")[-1]
            ocr_artifact_key = f"ocr/{job_id}/{basename}.json"

        raw = read_bytes_from_storage(ocr_artifact_key, storage)
        ocr_artifact = json.loads(raw.decode("utf-8"))
        structured = parse_ocr_artifact_to_structured(ocr_artifact)

        # Save structured artifact
        structured_key = f"results/{job_id}/{page_key.split('/')[-1]}.structured.json"
        storage.put_bytes(structured_key, json.dumps(structured, ensure_ascii=False).encode("utf-8"))
        logger.info("Saved structured artifact %s", structured_key)

        # If flagged for review or low confidence, append to active learning queue
        if structured.get("needs_review", False) or structured.get("confidence_score", 1.0) < 0.6:
            al_record = {
                "job_id": job_id,
                "page_key": page_key,
                "ocr_artifact_key": ocr_artifact_key,
                "structured_key": structured_key,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "confidence_score": structured.get("confidence_score"),
                "validation": structured.get("validation"),
            }
            _append_to_active_learning(al_record)

        # Placeholder: persist summary to DB (implement your own DB persistence)
        try:
            _persist_result_db_stub(job_id, structured_key, structured)
        except Exception:
            logger.exception("DB persistence stub failed - please implement persistence")

        return {"ok": True, "structured_key": structured_key, "needs_review": structured.get("needs_review", False)}
    except Exception as exc:
        logger.exception("semantic_parse_task failed job=%s page=%s", job_id, page_key)
        raise self.retry(exc=exc, countdown=min(60, (2 ** self.request.retries)))


# ---------- Persistence stub (replace with real DB writes) ----------
def _persist_result_db_stub(job_id: str, structured_key: str, structured: Dict[str, Any]) -> None:
    """
    Stub: persist a summary row/metadata into a results DB.
    Replace this function with your SQLAlchemy / DB code.

    Example fields to persist:
       - job_id
       - result_key (structured_key)
       - invoice_no
       - invoice_date
       - vendor
       - total
       - currency
       - confidence_score
       - needs_review boolean
    """
    logger.info("PERSIST STUB job=%s key=%s invoice_no=%s total=%s needs_review=%s",
                job_id, structured_key, structured.get("invoice_no"), structured.get("total"), structured.get("needs_review"))
    # TODO: implement DB write here (SQLAlchemy / async DB driver etc.)

