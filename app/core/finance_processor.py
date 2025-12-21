"""
Complete Finance Processing Pipeline

This module wires together all the finance data layer components:
1. Parse OCR → Invoice objects
2. Validate with math + business rules
3. Store at each ETL stage
4. Export for active learning
5. Compute metrics

Example usage:
    processor = FinanceProcessor()
    result = processor.process_invoice(ocr_json, invoice_id="INV-001")
"""
import logging
from typing import Dict, Any, Optional
from app.parsers.invoice_parser import parse_invoice_from_ocr
from app.validation.finance_validator import validate_invoice, ValidationResult
from app.storage.finance_etl import store_stage, get_etl_pipeline
from app.training.active_learning import export_training_example
from app.metrics.finance_metrics import compute_invoice_metrics
from app.models.finance import Invoice

logger = logging.getLogger(__name__)


class FinanceProcessor:
    """Complete finance processing pipeline."""
    
    def process_invoice(
        self,
        ocr_json: Dict[str, Any],
        invoice_id: Optional[str] = None,
        export_for_training: bool = False
    ) -> Dict[str, Any]:
        """
        Process an invoice through the complete ETL pipeline.
        
        Args:
            ocr_json: Raw OCR output
            invoice_id: Optional invoice identifier (will use from ocr_json if not provided)
            export_for_training: If True, export to training queue
            
        Returns:
            Complete processing result with validation and metrics
        """
        # Extract invoice ID
        invoice_id = invoice_id or ocr_json.get("invoice_id", "unknown")
        
        # Stage 1: Store raw OCR
        store_stage("raw_ocr", invoice_id, ocr_json)
        
        # Stage 2: Parse to Invoice object
        try:
            invoice = parse_invoice_from_ocr(ocr_json)
            parsed_data = invoice.model_dump()
            store_stage("parsed", invoice_id, parsed_data)
        except Exception as e:
            logger.error(f"Failed to parse invoice {invoice_id}: {e}")
            return {
                "invoice_id": invoice_id,
                "status": "error",
                "error": str(e),
                "stage": "parsing"
            }
        
        # Stage 3: Validate
        validation_result = validate_invoice(invoice)
        validated_data = {
            "invoice": parsed_data,
            "validation": validation_result.to_dict()
        }
        store_stage("validated", invoice_id, validated_data)
        
        # Stage 4: Export for training if requested
        if export_for_training:
            export_training_example(ocr_json, parsed_data, invoice_id)
        
        # Prepare result
        result = {
            "invoice_id": invoice_id,
            "status": "success" if validation_result.passed else "validation_failed",
            "invoice": parsed_data,
            "validation": validation_result.to_dict(),
            "confidence": invoice.confidence,
        }
        
        return result
    
    def correct_invoice(
        self,
        invoice_id: str,
        corrected_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store human-corrected invoice data (training gold standard).
        
        Args:
            invoice_id: Invoice identifier
            corrected_data: Corrected invoice data
            
        Returns:
            Confirmation with path to corrected data
        """
        store_stage("corrected", invoice_id, corrected_data)
        
        # Also export to training queue
        from app.storage.finance_etl import load_stage
        raw_data = load_stage("raw_ocr", invoice_id)
        if raw_data:
            export_training_example(
                raw_data.get("data", {}),
                corrected_data,
                invoice_id
            )
        
        return {
            "invoice_id": invoice_id,
            "status": "corrected",
            "message": "Corrected data stored and exported for training"
        }
    
    def get_metrics(self, invoices: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute aggregate metrics for a collection of invoices.
        
        Args:
            invoices: List of invoice result dictionaries
            
        Returns:
            Metrics dictionary
        """
        return compute_invoice_metrics(invoices)
    
    def get_pipeline_data(self, invoice_id: str) -> Dict[str, Any]:
        """
        Get complete ETL pipeline data for an invoice.
        
        Args:
            invoice_id: Invoice identifier
            
        Returns:
            Dictionary with data from all stages
        """
        return get_etl_pipeline(invoice_id)

