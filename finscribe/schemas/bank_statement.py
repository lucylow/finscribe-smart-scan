"""
Bank statement document schema.
"""

from .base import DocumentSchema, FieldSpec

BANK_STATEMENT_SCHEMA = DocumentSchema(
    doc_type="bank_statement",
    fields=[
        FieldSpec(
            "account_holder",
            required=True,
            region_type="header",
            description="Account holder name"
        ),
        FieldSpec(
            "account_number",
            required=True,
            region_type="header",
            regex=r"(account|acct)[\s#:]*[\d\-*]+",
            description="Account number (may be masked)"
        ),
        FieldSpec(
            "statement_period",
            required=False,
            region_type="header",
            regex=r"\d{1,2}[-/]\d{1,2}[-/]\d{4}\s+to\s+\d{1,2}[-/]\d{1,2}[-/]\d{4}",
            description="Statement period date range"
        ),
        FieldSpec(
            "transactions",
            required=True,
            region_type="table",
            description="List of transactions"
        ),
        FieldSpec(
            "opening_balance",
            required=False,
            region_type="footer",
            regex=r"(opening|beginning)\s+balance[\s:]*\$?\s*[\d,]+\.?\d*",
            description="Opening balance"
        ),
        FieldSpec(
            "closing_balance",
            required=True,
            region_type="footer",
            regex=r"(closing|ending)\s+balance[\s:]*\$?\s*[\d,]+\.?\d*",
            description="Closing balance"
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

