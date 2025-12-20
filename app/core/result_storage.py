"""
Result storage with schema versioning and lineage tracking.
"""
import json
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import os

from ..api.v1.schemas import (
    ResultResponse, FieldExtraction, FinancialSummary,
    ValidationResult, ModelInfo, Provenance
)

logger = logging.getLogger(__name__)


class ResultStorage:
    """Stores and retrieves results with versioning."""
    
    def __init__(self, storage_dir: str = "/tmp/finscribe_results"):
        """Initialize result storage."""
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def store_result(
        self,
        job_id: str,
        result_data: Dict[str, Any],
        provenance: Dict[str, Any]
    ) -> str:
        """
        Store result and return result_id.
        
        Args:
            job_id: Job identifier
            result_data: Processed result data
            provenance: Provenance information
            
        Returns:
            result_id: Unique result identifier
        """
        result_id = str(uuid.uuid4())
        
        # Build result response
        result = ResultResponse(
            schema_version="1.0",
            result_id=result_id,
            job_id=job_id,
            document_metadata=result_data.get("metadata", {}),
            extracted_fields=self._build_extracted_fields(result_data),
            financial_summary=self._build_financial_summary(result_data),
            validation_results=self._build_validation_results(result_data),
            models_used=self._build_models_used(result_data),
            provenance=Provenance(**provenance),
            created_at=datetime.utcnow(),
            processing_time_ms=result_data.get("metadata", {}).get("processing_time_ms")
        )
        
        # Store as JSON
        result_path = os.path.join(self.storage_dir, f"{result_id}.json")
        with open(result_path, "w") as f:
            f.write(result.model_dump_json(indent=2))
        
        logger.info(f"Stored result {result_id} for job {job_id}")
        return result_id
    
    def get_result(self, result_id: str) -> Optional[ResultResponse]:
        """Retrieve result by result_id."""
        result_path = os.path.join(self.storage_dir, f"{result_id}.json")
        
        if not os.path.exists(result_path):
            return None
        
        try:
            with open(result_path, "r") as f:
                data = json.load(f)
            
            return ResultResponse(**data)
        except Exception as e:
            logger.error(f"Error reading result {result_id}: {str(e)}")
            return None
    
    def _build_extracted_fields(self, result_data: Dict[str, Any]) -> list[FieldExtraction]:
        """Build extracted fields from result data."""
        fields = []
        extracted = result_data.get("extracted_data", [])
        
        for field_data in extracted:
            fields.append(FieldExtraction(
                field_name=field_data.get("field_name", ""),
                value=field_data.get("value"),
                confidence=field_data.get("confidence", 0.0),
                source_model=field_data.get("source_model", "unknown"),
                lineage_id=field_data.get("lineage_id", str(uuid.uuid4()))
            ))
        
        return fields
    
    def _build_financial_summary(self, result_data: Dict[str, Any]) -> Optional[FinancialSummary]:
        """Build financial summary from result data."""
        structured = result_data.get("structured_output", {})
        summary = structured.get("financial_summary", {})
        
        if not summary:
            return None
        
        return FinancialSummary(
            subtotal=summary.get("subtotal"),
            tax=summary.get("tax"),
            tax_rate=summary.get("tax_rate"),
            total=summary.get("total") or summary.get("grand_total"),
            currency=summary.get("currency", "USD"),
            line_items_count=len(structured.get("line_items", []))
        )
    
    def _build_validation_results(self, result_data: Dict[str, Any]) -> Optional[ValidationResult]:
        """Build validation results from result data."""
        validation = result_data.get("validation")
        
        if not validation:
            return None
        
        return ValidationResult(
            is_valid=validation.get("is_valid", False),
            math_ok=validation.get("math_ok", False),
            dates_ok=validation.get("dates_ok", False),
            issues=validation.get("issues", []),
            field_confidences=validation.get("field_confidences", {}),
            needs_review=validation.get("needs_review", False)
        )
    
    def _build_models_used(self, result_data: Dict[str, Any]) -> list[ModelInfo]:
        """Build models used list from result data."""
        models = []
        metadata = result_data.get("metadata", {})
        model_versions = metadata.get("model_versions", {})
        
        for model_name, version in model_versions.items():
            models.append(ModelInfo(
                name=model_name,
                version=version or "unknown"
            ))
        
        return models


# Global result storage instance
result_storage = ResultStorage()

