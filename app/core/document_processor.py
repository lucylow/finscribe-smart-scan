import os
import uuid
import json
import asyncio
import aiofiles
from typing import Dict, Any, List
from datetime import datetime
from PIL import Image
from io import BytesIO
import logging

from .models.paddleocr_vl_service import PaddleOCRVLService
from .models.ernie_vlm_service import ErnieVLMService
from .validation.financial_validator import FinancialValidator
from ..config.settings import load_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinancialDocumentProcessor:
    """
    Main orchestrator for processing financial documents.
    Combines PaddleOCR-VL for layout parsing with ERNIE 4.5 for semantic reasoning.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or load_config()
        
        # Initialize services
        self.ocr_service = PaddleOCRVLService(self.config)
        self.vlm_service = ErnieVLMService(self.config)
        self.validator = FinancialValidator(
            tolerance=self.config.get("validation", {}).get("arithmetic_tolerance", 0.01)
        )
        
        # Storage paths
        storage_config = self.config.get("storage", {})
        self.upload_dir = storage_config.get("upload_dir", "/tmp/finscribe_uploads")
        self.staging_dir = storage_config.get("staging_dir", "/tmp/finscribe_staging")
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.staging_dir, exist_ok=True)
        
        # Active learning
        al_config = self.config.get("active_learning", {})
        self.active_learning_enabled = al_config.get("enabled", True)
        self.active_learning_file = al_config.get("file_path", "./active_learning.jsonl")
    
    async def process_document(self, file_content: bytes, filename: str, model_type: str = "fine_tuned") -> Dict[str, Any]:
        """
        Complete pipeline: Parse document layout and apply financial reasoning.
        """
        document_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        logger.info(f"Processing document: {filename} (ID: {document_id})")
        
        # Validate inputs
        if not file_content or len(file_content) == 0:
            error_msg = "File content is empty"
            logger.error(f"{error_msg} for document: {filename}")
            return {
                "success": False,
                "document_id": document_id,
                "status": "failed",
                "error": error_msg,
                "extracted_data": [],
                "validation": None
            }
        
        ocr_results = None
        enriched_data = None
        validation_results = None
        
        try:
            # Step 1: Parse document layout with PaddleOCR-VL
            logger.info("Step 1: Running PaddleOCR-VL for document layout parsing...")
            try:
                ocr_results = await self.ocr_service.parse_document(file_content)
                
                # Validate OCR results
                if not ocr_results or not isinstance(ocr_results, dict):
                    raise ValueError("OCR service returned invalid results")
                
                if ocr_results.get("status") == "partial":
                    logger.warning("OCR returned partial results - continuing with available data")
                
            except Exception as ocr_error:
                logger.error(f"OCR processing failed: {str(ocr_error)}", exc_info=True)
                raise Exception(f"OCR processing failed: {str(ocr_error)}")
            
            # Step 2: Enrich with ERNIE 4.5 VLM for semantic understanding
            logger.info("Step 2: Enriching with ERNIE 4.5 for semantic reasoning...")
            try:
                enriched_data = await self.vlm_service.enrich_financial_data(ocr_results, file_content)
                
                # Validate VLM results
                if not enriched_data or not isinstance(enriched_data, dict):
                    raise ValueError("VLM service returned invalid results")
                
                if enriched_data.get("status") == "partial":
                    logger.warning("VLM returned partial results - continuing with available data")
                
                # Ensure structured_data exists
                if "structured_data" not in enriched_data:
                    enriched_data["structured_data"] = {}
                    logger.warning("VLM results missing structured_data - using empty structure")
                
            except Exception as vlm_error:
                logger.error(f"VLM enrichment failed: {str(vlm_error)}", exc_info=True)
                # Try to continue with OCR results only if VLM fails
                logger.warning("Continuing with OCR results only after VLM failure")
                enriched_data = {
                    "structured_data": {},
                    "status": "partial",
                    "error": f"VLM enrichment failed: {str(vlm_error)}"
                }
            
            # Step 3: Apply business rule validation
            logger.info("Step 3: Applying business rule validation...")
            try:
                validation_results = self.validator.validate(enriched_data)
            except Exception as validation_error:
                logger.error(f"Validation failed: {str(validation_error)}", exc_info=True)
                # Create a default validation result if validation fails
                validation_results = {
                    "is_valid": False,
                    "math_ok": False,
                    "dates_ok": False,
                    "issues": [f"Validation error: {str(validation_error)}"],
                    "field_confidences": {},
                    "needs_review": True
                }
            
            # Build extracted fields for frontend compatibility
            try:
                extracted_fields = self._build_extracted_fields(enriched_data, model_type)
            except Exception as field_error:
                logger.error(f"Error building extracted fields: {str(field_error)}", exc_info=True)
                extracted_fields = []
            
            # Step 4: Log to active learning if enabled (non-blocking)
            if self.active_learning_enabled and model_type == "fine_tuned":
                try:
                    await self._log_active_learning_data(
                        document_id, filename, enriched_data, validation_results
                    )
                except Exception as al_error:
                    logger.warning(f"Failed to log active learning data (non-critical): {str(al_error)}")
            
            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return {
                "success": True,
                "document_id": document_id,
                "status": "completed",
                "extracted_data": extracted_fields,
                "structured_output": enriched_data.get("structured_data", {}),
                "validation": validation_results,
                "raw_ocr_output": ocr_results or {},
                "metadata": {
                    "source_file": filename,
                    "processing_timestamp": start_time.isoformat(),
                    "processing_time_ms": processing_time_ms,
                    "model_versions": {
                        "paddleocr_vl": ocr_results.get("model_version", "PaddleOCR-VL-0.9B") if ocr_results else "unknown",
                        "ernie_vl": enriched_data.get("model_version", "ERNIE-4.5-VL-28B-A3B-Thinking") if enriched_data else "unknown"
                    },
                    "model_type": model_type,
                    "partial_results": ocr_results.get("status") == "partial" or enriched_data.get("status") == "partial" if enriched_data else False
                },
                "active_learning_ready": validation_results.get("needs_review", False) if validation_results else False
            }
            
        except Exception as e:
            logger.error(f"Error processing document {filename} (ID: {document_id}): {str(e)}", exc_info=True)
            return {
                "success": False,
                "document_id": document_id,
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "extracted_data": [],
                "validation": validation_results,
                "raw_ocr_output": ocr_results or {},
                "partial_results": ocr_results is not None or enriched_data is not None
            }
    
    def _build_extracted_fields(self, enriched_data: Dict[str, Any], model_type: str) -> List[Dict[str, Any]]:
        """Convert structured data to frontend-compatible extracted fields format."""
        fields = []
        structured = enriched_data.get("structured_data", {})
        confidences = enriched_data.get("confidence_scores", {})
        
        # Vendor info
        vendor = structured.get("vendor_block", {})
        if vendor.get("name"):
            fields.append({
                "field_name": "vendor_name",
                "value": vendor.get("name"),
                "confidence": vendor.get("confidence", 0.95),
                "source_model": f"ERNIE-4.5-VL ({model_type})",
                "lineage_id": str(uuid.uuid4())
            })
        
        # Client/Invoice info
        client = structured.get("client_info", {})
        if client.get("invoice_number"):
            fields.append({
                "field_name": "invoice_number",
                "value": client.get("invoice_number"),
                "confidence": client.get("confidence", 0.94),
                "source_model": f"ERNIE-4.5-VL ({model_type})",
                "lineage_id": str(uuid.uuid4())
            })
        if client.get("invoice_date"):
            fields.append({
                "field_name": "invoice_date",
                "value": client.get("invoice_date"),
                "confidence": client.get("confidence", 0.94),
                "source_model": f"ERNIE-4.5-VL ({model_type})",
                "lineage_id": str(uuid.uuid4())
            })
        
        # Financial summary
        summary = structured.get("financial_summary", {})
        if summary.get("subtotal"):
            fields.append({
                "field_name": "subtotal",
                "value": f"${summary.get('subtotal'):,.2f}",
                "confidence": 0.97,
                "source_model": f"ERNIE-4.5-VL ({model_type})",
                "lineage_id": str(uuid.uuid4())
            })
        if summary.get("grand_total"):
            fields.append({
                "field_name": "total",
                "value": f"${summary.get('grand_total'):,.2f}",
                "confidence": 0.98,
                "source_model": f"ERNIE-4.5-VL ({model_type})",
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
    
    async def _log_active_learning_data(
        self, 
        document_id: str, 
        filename: str, 
        enriched_data: Dict[str, Any],
        validation: Dict[str, Any]
    ):
        """Log data to active_learning.jsonl for LoRA SFT."""
        log_entry = {
            "document_id": document_id,
            "source_file": filename,
            "timestamp": datetime.utcnow().isoformat(),
            "model_output": enriched_data.get("structured_data", {}),
            "validation": validation,
            "needs_review": validation.get("needs_review", False),
            "difficulty_label": "medium" if validation.get("needs_review") else "easy",
            "error_type": validation.get("issues", [])[:1] if validation.get("issues") else None
        }
        
        try:
            async with aiofiles.open(self.active_learning_file, mode="a") as f:
                await f.write(json.dumps(log_entry) + "\n")
            logger.info(f"Logged active learning data for document {document_id}")
        except Exception as e:
            logger.warning(f"Could not log to active learning file: {e}")
    
    async def compare_models(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Process document with both fine-tuned and baseline configurations for comparison.
        """
        document_id = str(uuid.uuid4())
        
        # Validate inputs
        if not file_content or len(file_content) == 0:
            error_msg = "File content is empty"
            logger.error(f"{error_msg} for comparison: {filename}")
            return {
                "document_id": document_id,
                "status": "failed",
                "error": error_msg,
                "fine_tuned_result": None,
                "baseline_result": None,
                "comparison_summary": None
            }
        
        # Run with fine-tuned model
        fine_tuned_result = None
        try:
            fine_tuned_result = await self.process_document(file_content, filename, model_type="fine_tuned")
            if not fine_tuned_result.get("success", False):
                logger.warning(f"Fine-tuned model processing failed: {fine_tuned_result.get('error')}")
        except Exception as e:
            logger.error(f"Fine-tuned model processing exception: {str(e)}", exc_info=True)
            fine_tuned_result = {
                "success": False,
                "status": "failed",
                "error": str(e),
                "extracted_data": []
            }
        
        # Run with baseline model (simulated difference)
        baseline_result = None
        try:
            baseline_result = await self.process_document(file_content, filename, model_type="baseline")
            if not baseline_result.get("success", False):
                logger.warning(f"Baseline model processing failed: {baseline_result.get('error')}")
        except Exception as e:
            logger.error(f"Baseline model processing exception: {str(e)}", exc_info=True)
            baseline_result = {
                "success": False,
                "status": "failed",
                "error": str(e),
                "extracted_data": []
            }
        
        # Calculate comparison metrics (handle failures gracefully)
        try:
            ft_conf = self._avg_confidence(fine_tuned_result.get("extracted_data", []) if fine_tuned_result else [])
            bl_conf = self._avg_confidence(baseline_result.get("extracted_data", []) if baseline_result else [])
            
            comparison_summary = {
                "fine_tuned_confidence_avg": ft_conf,
                "baseline_confidence_avg": bl_conf,
                "confidence_improvement": f"{((ft_conf - bl_conf) / bl_conf * 100) if bl_conf > 0 else 0:.1f}%",
                "fine_tuned_fields_extracted": len(fine_tuned_result.get("extracted_data", []) if fine_tuned_result else []),
                "baseline_fields_extracted": len(baseline_result.get("extracted_data", []) if baseline_result else []),
                "fine_tuned_success": fine_tuned_result.get("success", False) if fine_tuned_result else False,
                "baseline_success": baseline_result.get("success", False) if baseline_result else False
            }
        except Exception as e:
            logger.error(f"Error calculating comparison metrics: {str(e)}", exc_info=True)
            comparison_summary = {
                "error": f"Failed to calculate comparison metrics: {str(e)}",
                "fine_tuned_success": fine_tuned_result.get("success", False) if fine_tuned_result else False,
                "baseline_success": baseline_result.get("success", False) if baseline_result else False
            }
        
        # Determine overall status
        if fine_tuned_result and baseline_result and fine_tuned_result.get("success") and baseline_result.get("success"):
            status = "completed"
        elif fine_tuned_result or baseline_result:
            status = "partial"
        else:
            status = "failed"
        
        return {
            "document_id": document_id,
            "status": status,
            "fine_tuned_result": fine_tuned_result,
            "baseline_result": baseline_result,
            "comparison_summary": comparison_summary
        }
    
    def _avg_confidence(self, fields: List[Dict[str, Any]]) -> float:
        """Calculate average confidence across extracted fields."""
        if not fields:
            return 0.0
        return sum(f.get("confidence", 0) for f in fields) / len(fields)


# Global processor instance
processor = FinancialDocumentProcessor()
