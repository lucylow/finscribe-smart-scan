"""
OCR → Structured Finance Parsing Layer

Turns raw OCR output into validated finance objects.
"""
from typing import Dict, Any
from decimal import Decimal
from datetime import date, datetime
from app.models.finance import Invoice, Vendor, LineItem, Money


def parse_invoice_from_ocr(ocr_json: Dict[str, Any]) -> Invoice:
    """
    Parse raw OCR JSON output into validated Invoice object.
    
    Args:
        ocr_json: Raw OCR output dictionary with invoice data
        
    Returns:
        Validated Invoice object
        
    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Parse vendor information
    vendor_data = ocr_json.get("vendor", {})
    vendor = Vendor(
        name=vendor_data.get("name", ""),
        address=vendor_data.get("address"),
        tax_id=vendor_data.get("tax_id"),
    )
    
    # Parse line items
    line_items = []
    for row in ocr_json.get("line_items", []):
        line_items.append(
            LineItem(
                description=row.get("description", ""),
                quantity=Decimal(str(row.get("quantity", "1"))),
                unit_price=Money(
                    value=Decimal(str(row.get("unit_price", "0"))),
                    currency=row.get("currency", "USD")
                ),
                total=Money(
                    value=Decimal(str(row.get("total", "0"))),
                    currency=row.get("currency", "USD")
                ),
            )
        )
    
    # Parse invoice date
    invoice_date_str = ocr_json.get("invoice_date", "")
    if isinstance(invoice_date_str, str):
        # Try to parse date string
        try:
            invoice_date = datetime.strptime(invoice_date_str, "%Y-%m-%d").date()
        except ValueError:
            try:
                invoice_date = datetime.strptime(invoice_date_str, "%m/%d/%Y").date()
            except ValueError:
                # Fallback to today if parsing fails
                invoice_date = date.today()
    elif isinstance(invoice_date_str, date):
        invoice_date = invoice_date_str
    else:
        invoice_date = date.today()
    
    # Parse financial summary
    subtotal_value = Decimal(str(ocr_json.get("subtotal", "0")))
    tax_value = ocr_json.get("tax")
    total_value = Decimal(str(ocr_json.get("total", "0")))
    
    currency = ocr_json.get("currency", "USD")
    
    return Invoice(
        invoice_id=ocr_json.get("invoice_id", ""),
        invoice_date=invoice_date,
        vendor=vendor,
        line_items=line_items,
        subtotal=Money(value=subtotal_value, currency=currency),
        tax=Money(value=Decimal(str(tax_value)), currency=currency) if tax_value else None,
        total=Money(value=total_value, currency=currency),
        confidence=ocr_json.get("confidence", 0.0),
    )

