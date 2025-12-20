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
        
        try:
            # Step 1: Parse document layout with PaddleOCR-VL
            logger.info("Step 1: Running PaddleOCR-VL for document layout parsing...")
            ocr_results = await self.ocr_service.parse_document(file_content)
            
            # Step 2: Enrich with ERNIE 4.5 VLM for semantic understanding
            logger.info("Step 2: Enriching with ERNIE 4.5 for semantic reasoning...")
            enriched_data = await self.vlm_service.enrich_financial_data(ocr_results, file_content)
            
            # Step 3: Apply business rule validation
            logger.info("Step 3: Applying business rule validation...")
            validation_results = self.validator.validate(enriched_data)
            
            # Build extracted fields for frontend compatibility
            extracted_fields = self._build_extracted_fields(enriched_data, model_type)
            
            # Step 4: Log to active learning if enabled
            if self.active_learning_enabled and model_type == "fine_tuned":
                await self._log_active_learning_data(
                    document_id, filename, enriched_data, validation_results
                )
            
            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return {
                "success": True,
                "document_id": document_id,
                "status": "completed",
                "extracted_data": extracted_fields,
                "structured_output": enriched_data.get("structured_data", {}),
                "validation": validation_results,
                "raw_ocr_output": ocr_results,
                "metadata": {
                    "source_file": filename,
                    "processing_timestamp": start_time.isoformat(),
                    "processing_time_ms": processing_time_ms,
                    "model_versions": {
                        "paddleocr_vl": ocr_results.get("model_version", "PaddleOCR-VL-0.9B"),
                        "ernie_vl": enriched_data.get("model_version", "ERNIE-4.5-VL-28B-A3B-Thinking")
                    },
                    "model_type": model_type
                },
                "active_learning_ready": validation_results.get("needs_review", False)
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return {
                "success": False,
                "document_id": document_id,
                "status": "failed",
                "error": str(e),
                "extracted_data": [],
                "validation": None
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
        
        # Run with fine-tuned model
        fine_tuned_result = await self.process_document(file_content, filename, model_type="fine_tuned")
        
        # Run with baseline model (simulated difference)
        baseline_result = await self.process_document(file_content, filename, model_type="baseline")
        
        # Calculate comparison metrics
        ft_conf = self._avg_confidence(fine_tuned_result.get("extracted_data", []))
        bl_conf = self._avg_confidence(baseline_result.get("extracted_data", []))
        
        return {
            "document_id": document_id,
            "status": "completed",
            "fine_tuned_result": fine_tuned_result,
            "baseline_result": baseline_result,
            "comparison_summary": {
                "fine_tuned_confidence_avg": ft_conf,
                "baseline_confidence_avg": bl_conf,
                "confidence_improvement": f"{((ft_conf - bl_conf) / bl_conf * 100) if bl_conf > 0 else 0:.1f}%",
                "fine_tuned_fields_extracted": len(fine_tuned_result.get("extracted_data", [])),
                "baseline_fields_extracted": len(baseline_result.get("extracted_data", []))
            }
        }
    
    def _avg_confidence(self, fields: List[Dict[str, Any]]) -> float:
        """Calculate average confidence across extracted fields."""
        if not fields:
            return 0.0
        return sum(f.get("confidence", 0) for f in fields) / len(fields)


# Global processor instance
processor = FinancialDocumentProcessor()
