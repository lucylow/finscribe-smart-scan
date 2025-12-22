"""
Receipt document schema.
"""

from .base import DocumentSchema, FieldSpec

RECEIPT_SCHEMA = DocumentSchema(
    doc_type="receipt",
    fields=[
        FieldSpec(
            "merchant",
            required=True,
            region_type="header",
            description="Merchant/store name"
        ),
        FieldSpec(
            "date",
            required=True,
            region_type="header",
            regex=r"\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}",
            description="Transaction date"
        ),
        FieldSpec(
            "time",
            required=False,
            region_type="header",
            regex=r"\d{1,2}:\d{2}(?:\s*[AP]M)?",
            description="Transaction time"
        ),
        FieldSpec(
            "items",
            required=True,
            region_type="table",
            description="List of purchased items"
        ),
        FieldSpec(
            "total",
            required=True,
            region_type="footer",
            regex=r"(total|amount)[\s:]*\$?\s*[\d,]+\.?\d*",
            description="Total amount"
        ),
        FieldSpec(
            "tax",
            required=False,
            region_type="footer",
            regex=r"(tax|sales tax)[\s:]*\$?\s*[\d,]+\.?\d*",
            description="Tax amount"
        ),
        FieldSpec(
            "payment_method",
            required=False,
            region_type="footer",
            regex=r"(cash|credit|debit|card|check)",
            description="Payment method used"
        ),
        FieldSpec(
            "currency",
            required=True,
            region_type="footer",
            regex=r"\b(USD|EUR|GBP|CAD|JPY|CNY|AUD|CHF|INR)\b",
            description="Currency code"
        ),
    ],
)

