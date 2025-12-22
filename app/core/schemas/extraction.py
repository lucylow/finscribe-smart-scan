"""
Pydantic schemas for document extraction results.

These schemas define the structure of extracted financial data with:
- Confidence scores for each field
- Source region (bounding box coordinates) for traceability
- Model version information
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ExtractedField(BaseModel):
    """A single extracted field with metadata."""
    
    field_name: str = Field(..., description="Name of the extracted field")
    value: Any = Field(..., description="Extracted value")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    source_model: str = Field(..., description="Model that extracted this field")
    lineage_id: str = Field(..., description="Unique identifier for traceability")
    source_region: Optional[List[int]] = Field(
        None,
        description="Bounding box coordinates [x1, y1, x2, y2] from OCR"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field_name": "vendor_name",
                "value": "Acme Corporation",
                "confidence": 0.98,
                "source_model": "ERNIE-5 (fine_tuned)",
                "lineage_id": "550e8400-e29b-41d4-a716-446655440000",
                "source_region": [100, 120, 800, 420]
            }
        }
    )


class LineItem(BaseModel):
    """A single line item from an invoice."""
    
    description: str = Field(..., description="Item description")
    quantity: float = Field(..., ge=0.0, description="Quantity")
    unit_price: float = Field(..., ge=0.0, description="Unit price")
    line_total: float = Field(..., ge=0.0, description="Line total (quantity × unit_price)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    bbox: Optional[List[int]] = Field(
        None,
        description="Bounding box coordinates [x1, y1, x2, y2]"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Professional Services",
                "quantity": 10.0,
                "unit_price": 150.0,
                "line_total": 1500.0,
                "confidence": 0.95,
                "bbox": [50, 500, 800, 550]
            }
        }
    )


class FinancialSummary(BaseModel):
    """Financial summary with totals."""
    
    subtotal: float = Field(..., ge=0.0, description="Subtotal before tax")
    tax_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="Tax rate (0.0-1.0)")
    tax_amount: Optional[float] = Field(None, ge=0.0, description="Tax amount")
    discount: Optional[float] = Field(None, ge=0.0, description="Discount amount")
    grand_total: float = Field(..., ge=0.0, description="Grand total")
    currency: str = Field(default="USD", description="Currency code (ISO 4217)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subtotal": 1500.0,
                "tax_rate": 0.1,
                "tax_amount": 150.0,
                "discount": 0.0,
                "grand_total": 1650.0,
                "currency": "USD"
            }
        }
    )


class VendorInfo(BaseModel):
    """Vendor information."""
    
    name: Optional[str] = Field(None, description="Vendor name")
    address: Optional[Dict[str, Any]] = Field(None, description="Vendor address")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="Confidence score")
    bbox: Optional[List[int]] = Field(None, description="Bounding box coordinates")


class ClientInfo(BaseModel):
    """Client/customer information."""
    
    invoice_number: Optional[str] = Field(None, description="Invoice number")
    invoice_date: Optional[str] = Field(None, description="Invoice date (ISO format)")
    due_date: Optional[str] = Field(None, description="Due date (ISO format)")
    client_name: Optional[str] = Field(None, description="Client name")
    confidence: float = Field(default=0.94, ge=0.0, le=1.0, description="Confidence score")
    bbox: Optional[List[int]] = Field(None, description="Bounding box coordinates")


class ExtractedDocument(BaseModel):
    """Complete extracted document structure."""
    
    document_type: str = Field(..., description="Document type (invoice, receipt, statement)")
    vendor: Optional[VendorInfo] = Field(None, description="Vendor information")
    client: Optional[ClientInfo] = Field(None, description="Client information")
    line_items: List[LineItem] = Field(default_factory=list, description="Line items")
    financial_summary: FinancialSummary = Field(..., description="Financial summary")
    schema_version: str = Field(default="v1", description="Schema version")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_type": "invoice",
                "vendor": {
                    "name": "Acme Corporation",
                    "confidence": 0.98
                },
                "client": {
                    "invoice_number": "INV-2024-001",
                    "invoice_date": "2024-03-15",
                    "confidence": 0.94
                },
                "line_items": [
                    {
                        "description": "Professional Services",
                        "quantity": 10.0,
                        "unit_price": 150.0,
                        "line_total": 1500.0,
                        "confidence": 0.95
                    }
                ],
                "financial_summary": {
                    "subtotal": 1500.0,
                    "tax_rate": 0.1,
                    "tax_amount": 150.0,
                    "grand_total": 1650.0,
                    "currency": "USD"
                },
                "schema_version": "v1"
            }
        }
    )


class ExtractionResult(BaseModel):
    """Complete extraction result with metadata."""
    
    document_id: str = Field(..., description="Unique document identifier")
    status: str = Field(..., description="Extraction status (completed, failed, partial)")
    extracted_document: Optional[ExtractedDocument] = Field(None, description="Extracted document")
    extracted_fields: List[ExtractedField] = Field(default_factory=list, description="Extracted fields")
    models_used: Dict[str, str] = Field(default_factory=dict, description="Model versions used")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "extracted_document": {
                    "document_type": "invoice",
                    "financial_summary": {
                        "subtotal": 1500.0,
                        "grand_total": 1650.0,
                        "currency": "USD"
                    }
                },
                "models_used": {
                    "ocr": "PaddleOCR-VL-0.9B",
                    "vlm": "ERNIE-5"
                },
                "processing_time_ms": 1850.5
            }
        }
    )

