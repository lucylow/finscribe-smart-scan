"""Invoice processing pipeline"""
import os
import time
import uuid
from decimal import Decimal
from typing import Dict, Any, Optional
from pathlib import Path

from backend.ocr.preprocess import preprocess_image
from backend.ocr.paddle_client import run_paddleocr
from backend.llm.ernie_client import call_ernie_validate, mock_ernie_response
from backend.storage.etl import store_stage
from backend.utils.safe_json import safe_json_parse
from backend.models.finance import (
    StructuredInvoice,
    ValidationResult,
    InvoiceResponse,
    Vendor,
    LineItem,
    FinancialSummary
)


def run_full_pipeline(input_path: str, use_ernie: bool = True) -> Dict[str, Any]:
    """
    Run full invoice processing pipeline.
    
    Steps:
    1. Preprocess image
    2. Run OCR
    3. Parse regions and extract structured data
    4. Validate with ERNIE (or fallback)
    5. Store stages
    6. Return response
    
    Args:
        input_path: Path to input image
        use_ernie: Whether to use ERNIE validation (falls back if unavailable)
        
    Returns:
        InvoiceResponse as dictionary
    """
    pipeline_start = time.time()
    invoice_id = str(uuid.uuid4())
    latency_breakdown = {}
    fallback_used = False
    
    try:
        # Step 1: Preprocess
        preprocess_start = time.time()
        preprocessed_path = preprocess_image(input_path)
        latency_breakdown["preprocess"] = int((time.time() - preprocess_start) * 1000)
        
        store_stage("preprocessed", invoice_id, {"path": preprocessed_path})
        
        # Step 2: OCR
        ocr_start = time.time()
        ocr_result = run_paddleocr(preprocessed_path)
        latency_breakdown["ocr"] = ocr_result.get("latency_ms", 0)
        
        store_stage("ocr", invoice_id, ocr_result)
        
        ocr_text = ocr_result.get("raw_text", "")
        ocr_words = ocr_result.get("words", [])
        
        # Step 3: Parse regions
        parse_start = time.time()
        structured_invoice = parse_regions(ocr_result, invoice_id)
        latency_breakdown["parse"] = int((time.time() - parse_start) * 1000)
        
        store_stage("parsed", invoice_id, structured_invoice.dict())
        
        # Step 4: Validate
        validation_start = time.time()
        validation_result = None
        
        if use_ernie:
            try:
                ernie_result = call_ernie_validate(structured_invoice.dict(), ocr_text)
                validation_result = ValidationResult(
                    is_valid=ernie_result.get("ok", False),
                    errors=ernie_result.get("errors", []),
                    field_confidences={"overall": ernie_result.get("confidence", 0.8)}
                )
                # Update invoice with validated data if provided
                if "validated_invoice" in ernie_result:
                    validated = ernie_result["validated_invoice"]
                    structured_invoice = StructuredInvoice(**validated)
            except Exception as e:
                print(f"Warning: ERNIE validation failed ({e}), using basic validator")
                fallback_used = True
                validation_result = basic_validator(structured_invoice)
        else:
            fallback_used = True
            validation_result = basic_validator(structured_invoice)
        
        latency_breakdown["validation"] = int((time.time() - validation_start) * 1000)
        
        store_stage("validated", invoice_id, validation_result.dict())
        
        # Compute overall confidence
        confidence = validation_result.field_confidences.get("overall", 0.8)
        if validation_result.is_valid:
            confidence = max(confidence, 0.85)
        
        # Build response
        total_latency = int((time.time() - pipeline_start) * 1000)
        latency_breakdown["total"] = total_latency
        
        response = InvoiceResponse(
            invoice_id=invoice_id,
            structured_invoice=structured_invoice,
            validation=validation_result,
            confidence=confidence,
            latency_ms=latency_breakdown,
            fallback_used=fallback_used
        )
        
        return response.dict()
        
    except Exception as e:
        # Return error response
        return {
            "invoice_id": invoice_id,
            "error": str(e),
            "latency_ms": latency_breakdown,
            "fallback_used": fallback_used
        }


def parse_regions(ocr_result: Dict[str, Any], invoice_id: str) -> StructuredInvoice:
    """
    Parse OCR result into structured invoice.
    
    Uses keyword-based extraction and table detection heuristics.
    """
    raw_text = ocr_result.get("raw_text", "")
    words = ocr_result.get("words", [])
    
    # Extract invoice number
    invoice_number = _extract_field(raw_text, ["Invoice #", "Invoice No", "Invoice Number", "INV"])
    
    # Extract date
    invoice_date = _extract_field(raw_text, ["Date:", "Invoice Date", "Date"])
    
    # Extract vendor name (look for common patterns)
    vendor_name = _extract_vendor_name(raw_text, words)
    vendor_address = _extract_vendor_address(raw_text)
    
    vendor = Vendor(
        name=vendor_name or "Unknown Vendor",
        address=vendor_address
    )
    
    # Extract line items (table detection)
    line_items = _extract_line_items(raw_text, words)
    
    # Extract financial summary
    financial_summary = _extract_financial_summary(raw_text)
    
    return StructuredInvoice(
        invoice_id=invoice_id,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        vendor=vendor,
        line_items=line_items,
        financial_summary=financial_summary
    )


def _extract_field(text: str, keywords: list) -> Optional[str]:
    """Extract field value after keyword"""
    text_lower = text.lower()
    for keyword in keywords:
        idx = text_lower.find(keyword.lower())
        if idx >= 0:
            # Find the value after the keyword
            start = idx + len(keyword)
            line = text[idx:idx + 200].split("\n")[0]
            value = line[len(keyword):].strip().strip(":").strip()
            if value:
                return value
    return None


def _extract_vendor_name(text: str, words: list) -> Optional[str]:
    """Extract vendor name (usually near top, before address)"""
    lines = text.split("\n")
    for i, line in enumerate(lines[:10]):  # Check first 10 lines
        line_lower = line.lower()
        if any(kw in line_lower for kw in ["inc", "ltd", "corp", "llc", "company"]):
            # Clean up common prefixes
            for prefix in ["Vendor:", "From:", "Bill From:"]:
                if line.startswith(prefix):
                    return line[len(prefix):].strip()
            return line.strip()
    return None


def _extract_vendor_address(text: str) -> Optional[str]:
    """Extract vendor address (multi-line after vendor name)"""
    lines = text.split("\n")
    address_lines = []
    in_address = False
    
    for line in lines[:15]:
        line_stripped = line.strip()
        if not line_stripped:
            if in_address:
                break
            continue
        
        # Look for address patterns
        if any(char.isdigit() for char in line_stripped) and any(
            kw in line_stripped.lower() for kw in ["street", "st", "ave", "blvd", "road", "rd"]
        ):
            in_address = True
        
        if in_address:
            address_lines.append(line_stripped)
            if len(address_lines) >= 3:  # Usually 2-3 lines
                break
    
    return "\n".join(address_lines) if address_lines else None


def _extract_line_items(text: str, words: list) -> list:
    """Extract line items from table"""
    line_items = []
    lines = text.split("\n")
    
    # Find table section (look for "Description", "Qty", "Price" headers)
    table_start = -1
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw in line_lower for kw in ["description", "qty", "quantity", "unit price", "total"]):
            table_start = i + 1
            break
    
    if table_start < 0:
        return []
    
    # Parse table rows
    for line in lines[table_start:table_start + 20]:  # Check up to 20 rows
        line = line.strip()
        if not line or any(kw in line.lower() for kw in ["subtotal", "tax", "total", "---"]):
            break
        
        # Try to extract: description, qty, unit_price, line_total
        parts = line.split()
        if len(parts) >= 3:
            # Look for numeric values (prices)
            nums = []
            desc_parts = []
            
            for part in parts:
                # Check if it's a price/number
                clean_part = part.replace("$", "").replace(",", "")
                try:
                    num = float(clean_part)
                    nums.append(num)
                except ValueError:
                    desc_parts.append(part)
            
            if len(nums) >= 2:  # At least qty and price
                description = " ".join(desc_parts) if desc_parts else "Item"
                qty = Decimal(str(nums[0]))
                unit_price = Decimal(str(nums[1]))
                line_total = qty * unit_price if len(nums) < 3 else Decimal(str(nums[2]))
                
                line_items.append(LineItem(
                    description=description,
                    quantity=qty,
                    unit_price=unit_price,
                    line_total=line_total
                ))
    
    return line_items


def _extract_financial_summary(text: str) -> FinancialSummary:
    """Extract financial summary (subtotal, tax, total)"""
    text_lower = text.lower()
    
    # Extract subtotal
    subtotal = _extract_currency_value(text, ["subtotal", "sub-total"])
    
    # Extract tax
    tax_amount = _extract_currency_value(text, ["tax", "tax amount", "tax:"])
    tax_rate = None
    # Try to extract tax rate
    for line in text.split("\n"):
        if "tax" in line.lower() and "%" in line:
            try:
                import re
                match = re.search(r"(\d+\.?\d*)%", line)
                if match:
                    tax_rate = Decimal(match.group(1)) / 100
            except:
                pass
    
    # Extract grand total
    grand_total = _extract_currency_value(text, ["grand total", "total", "amount due", "total:"])
    
    # Defaults if not found
    subtotal = subtotal or Decimal("0")
    tax_amount = tax_amount or Decimal("0")
    grand_total = grand_total or (subtotal + tax_amount)
    
    return FinancialSummary(
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        grand_total=grand_total,
        currency="USD"
    )


def _extract_currency_value(text: str, keywords: list) -> Optional[Decimal]:
    """Extract currency value after keyword"""
    text_lower = text.lower()
    for keyword in keywords:
        idx = text_lower.find(keyword.lower())
        if idx >= 0:
            # Find dollar amount after keyword
            line = text[idx:idx + 100]
            import re
            # Look for $X.XX pattern
            match = re.search(r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', line)
            if match:
                value_str = match.group(1).replace(",", "")
                try:
                    return Decimal(value_str)
                except:
                    pass
    return None


def basic_validator(structured_invoice: StructuredInvoice) -> ValidationResult:
    """
    Basic deterministic validator (arithmetic checks).
    
    Used as fallback when ERNIE is unavailable.
    """
    errors = []
    field_confidences = {}
    
    # Check line items arithmetic
    line_items = structured_invoice.line_items
    financial_summary = structured_invoice.financial_summary
    
    computed_subtotal = sum(item.line_total for item in line_items)
    subtotal = financial_summary.subtotal
    tax_amount = financial_summary.tax_amount
    grand_total = financial_summary.grand_total
    
    tolerance = Decimal("0.02")  # 2% tolerance
    
    # Check subtotal
    if abs(computed_subtotal - subtotal) / max(abs(subtotal), Decimal("1")) > tolerance:
        errors.append(f"Subtotal mismatch: computed {computed_subtotal}, found {subtotal}")
        field_confidences["subtotal"] = 0.5
    else:
        field_confidences["subtotal"] = 0.95
    
    # Check grand total
    expected_total = subtotal + tax_amount
    if abs(expected_total - grand_total) / max(abs(grand_total), Decimal("1")) > tolerance:
        errors.append(f"Grand total mismatch: expected {expected_total}, found {grand_total}")
        field_confidences["grand_total"] = 0.5
    else:
        field_confidences["grand_total"] = 0.95
    
    # Overall confidence
    if errors:
        field_confidences["overall"] = 0.65
    else:
        field_confidences["overall"] = 0.90
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        field_confidences=field_confidences
    )
