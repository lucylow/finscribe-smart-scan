"""
Validation Service - Handles business rule validation.

This service validates extracted financial data against business rules:
- Arithmetic checks (subtotal + tax = total)
- Date logic validation
- Required field presence
- Currency normalization
"""

import logging
from typing import Dict, Any, Optional

from ..validation.financial_validator import FinancialValidator
from ...config.settings import load_config

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Service for validating extracted financial data.
    
    Responsibilities:
    - Arithmetic validation (totals, line items)
    - Date logic validation
    - Required field checks
    - Confidence scoring
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize validation service with configuration."""
        self.config = config or load_config()
        
        tolerance = self.config.get("validation", {}).get("arithmetic_tolerance", 0.01)
        self.validator = FinancialValidator(tolerance=tolerance)
    
    def validate_extraction(
        self,
        enriched_data: Dict[str, Any],
        receipt_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate extracted financial data.
        
        Args:
            enriched_data: LLM/VLM enriched data
            receipt_data: Receipt-specific data (if applicable)
        
        Returns:
            Validation result dictionary with:
            - is_valid: Boolean indicating overall validity
            - math_ok: Arithmetic checks passed
            - dates_ok: Date logic checks passed
            - issues: List of validation issues
            - field_confidences: Confidence scores per field
            - needs_review: Whether human review is needed
        """
        try:
            if receipt_data:
                # Use receipt-specific validation
                validation_results = receipt_data.get("validation", {
                    "is_valid": True,
                    "errors": [],
                    "warnings": []
                })
                
                # Convert to standard format
                return {
                    "is_valid": validation_results.get("is_valid", True),
                    "math_ok": validation_results.get("math_ok", True),
                    "dates_ok": validation_results.get("dates_ok", True),
                    "issues": validation_results.get("errors", []) + validation_results.get("warnings", []),
                    "field_confidences": {},
                    "needs_review": not validation_results.get("is_valid", True)
                }
            else:
                # Use standard financial document validation
                return self.validator.validate(enriched_data)
        
        except Exception as validation_error:
            logger.error(f"Validation failed: {str(validation_error)}", exc_info=True)
            return {
                "is_valid": False,
                "math_ok": False,
                "dates_ok": False,
                "issues": [f"Validation error: {str(validation_error)}"],
                "field_confidences": {},
                "needs_review": True
            }
    
    def build_extracted_fields(
        self,
        enriched_data: Dict[str, Any],
        model_type: str = "fine_tuned"
    ) -> list:
        """
        Convert structured data to frontend-compatible extracted fields format.
        
        Args:
            enriched_data: LLM/VLM enriched data
            model_type: Model type used
        
        Returns:
            List of extracted field dictionaries
        """
        import uuid
        
        fields = []
        structured = enriched_data.get("structured_data", {})
        confidences = enriched_data.get("confidence_scores", {})
        
        model_name = enriched_data.get("model_version", "ERNIE-VLM")
        model_family = enriched_data.get("model_family", "ernie-5")
        source_model_label = f"{model_name} ({model_type})"
        
        # Handle receipt vs invoice structure
        if structured.get("document_type") == "receipt":
            merchant = structured.get("merchant_info", {})
            if merchant.get("name"):
                fields.append({
                    "field_name": "merchant_name",
                    "value": merchant.get("name"),
                    "confidence": 0.95,
                    "source_model": source_model_label,
                    "lineage_id": str(uuid.uuid4())
                })
        else:
            # Vendor info (for invoices)
            vendor = structured.get("vendor_block", {})
            if vendor.get("name"):
                fields.append({
                    "field_name": "vendor_name",
                    "value": vendor.get("name"),
                    "confidence": vendor.get("confidence", 0.95),
                    "source_model": source_model_label,
                    "lineage_id": str(uuid.uuid4())
                })
        
        # Client/Invoice info
        client = structured.get("client_info", {})
        if client.get("invoice_number"):
            fields.append({
                "field_name": "invoice_number",
                "value": client.get("invoice_number"),
                "confidence": client.get("confidence", 0.94),
                "source_model": source_model_label,
                "lineage_id": str(uuid.uuid4())
            })
        if client.get("invoice_date"):
            fields.append({
                "field_name": "invoice_date",
                "value": client.get("invoice_date"),
                "confidence": client.get("confidence", 0.94),
                "source_model": source_model_label,
                "lineage_id": str(uuid.uuid4())
            })
        
        # Financial summary
        summary = structured.get("financial_summary", {})
        if summary.get("subtotal"):
            fields.append({
                "field_name": "subtotal",
                "value": f"${summary.get('subtotal'):,.2f}",
                "confidence": 0.97,
                "source_model": source_model_label,
                "lineage_id": str(uuid.uuid4())
            })
        if summary.get("grand_total"):
            fields.append({
                "field_name": "total",
                "value": f"${summary.get('grand_total'):,.2f}",
                "confidence": 0.98,
                "source_model": source_model_label,
                "lineage_id": str(uuid.uuid4())
            })
        
        # Line items count
        line_items = structured.get("line_items", [])
        if line_items:
            fields.append({
                "field_name": "line_items_count",
                "value": str(len(line_items)),
                "confidence": confidences.get("line_items", 0.95),
                "source_model": f"PaddleOCR-VL ({model_type})",
                "lineage_id": str(uuid.uuid4())
            })
        
        return fields

