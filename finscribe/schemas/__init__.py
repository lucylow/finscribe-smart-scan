"""
Document schema definitions.

Provides layout-aware schemas for different financial document types.
"""

from .base import DocumentSchema, FieldSpec
from .invoice import INVOICE_SCHEMA
from .receipt import RECEIPT_SCHEMA
from .bank_statement import BANK_STATEMENT_SCHEMA

__all__ = [
    "DocumentSchema",
    "FieldSpec",
    "INVOICE_SCHEMA",
    "RECEIPT_SCHEMA",
    "BANK_STATEMENT_SCHEMA",
]


def infer_doc_type(text: str) -> str:
    """
    Auto-detect document type from text content.
    
    Args:
        text: Document text content
        
    Returns:
        Document type string: 'invoice', 'receipt', 'bank_statement', or 'generic'
    """
    text_lower = text.lower()
    
    # Check for invoice indicators
    if any(keyword in text_lower for keyword in ["invoice", "invoice number", "bill to"]):
        return "invoice"
    
    # Check for bank statement indicators
    if any(keyword in text_lower for keyword in ["statement", "account statement", "bank statement", "closing balance"]):
        return "bank_statement"
    
    # Check for receipt indicators
    if any(keyword in text_lower for keyword in ["receipt", "thank you", "purchase", "transaction"]):
        return "receipt"
    
    return "generic"


def get_schema_for_doc_type(doc_type: str) -> DocumentSchema:
    """
    Get schema for a document type.
    
    Args:
        doc_type: Document type string
        
    Returns:
        DocumentSchema instance
    """
    schemas = {
        "invoice": INVOICE_SCHEMA,
        "receipt": RECEIPT_SCHEMA,
        "bank_statement": BANK_STATEMENT_SCHEMA,
    }
    
    return schemas.get(doc_type, INVOICE_SCHEMA)  # Default to invoice schema

