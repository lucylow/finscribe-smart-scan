"""
Invoice document schema with layout-aware field specifications.
"""

from .base import DocumentSchema, FieldSpec

INVOICE_SCHEMA = DocumentSchema(
    doc_type="invoice",
    fields=[
        FieldSpec(
            "vendor_name",
            required=True,
            region_type="header",
            description="Name of the vendor/seller"
        ),
        FieldSpec(
            "invoice_no",
            required=True,
            region_type="header",
            regex=r"(INV|Invoice)[\s#:]*[A-Z0-9\-]+",
            description="Invoice number/identifier"
        ),
        FieldSpec(
            "invoice_date",
            required=True,
            region_type="header",
            regex=r"\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4}",
            description="Invoice date"
        ),
        FieldSpec(
            "due_date",
            required=False,
            region_type="header",
            regex=r"(due|due date)[\s:]*\d{4}[-/]\d{2}[-/]\d{2}",
            description="Payment due date"
        ),
        FieldSpec(
            "client_name",
            required=False,
            region_type="header",
            description="Name of the client/buyer"
        ),
        FieldSpec(
            "line_items",
            required=True,
            region_type="table",
            description="List of line items/products"
        ),
        FieldSpec(
            "subtotal",
            required=False,
            region_type="footer",
            regex=r"subtotal[\s:]*\$?\s*[\d,]+\.?\d*",
            description="Subtotal amount"
        ),
        FieldSpec(
            "tax",
            required=False,
            region_type="footer",
            regex=r"(tax|sales tax|vat)[\s:]*\$?\s*[\d,]+\.?\d*",
            description="Tax amount"
        ),
        FieldSpec(
            "total",
            required=True,
            region_type="footer",
            regex=r"(total|grand total|amount due)[\s:]*\$?\s*[\d,]+\.?\d*",
            description="Total amount"
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

