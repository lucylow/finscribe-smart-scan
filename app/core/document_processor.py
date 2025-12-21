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
# Import from the module file, not the package directory
import sys
import os
_post_processing_module_path = os.path.join(os.path.dirname(__file__), 'post_processing.py')
if os.path.exists(_post_processing_module_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("post_processing_module", _post_processing_module_path)
    post_processing_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(post_processing_module)
    FinancialDocumentPostProcessor = post_processing_module.FinancialDocumentPostProcessor
else:
    # Fallback to package if module doesn't exist
    from .post_processing.intelligence import FinancialPostProcessor as FinancialDocumentPostProcessor
from ..config.settings import load_config
from finscribe.receipts.processor import ReceiptProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinancialDocumentProcessor:
    """
    Main orchestrator for processing financial documents.
    Combines PaddleOCR-VL for layout parsing with ERNIE (4.5/5) for semantic reasoning.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or load_config()
        
        # Initialize services
        self.ocr_service = PaddleOCRVLService(self.config)
        self.vlm_service = ErnieVLMService(self.config)
        self.validator = FinancialValidator(
            tolerance=self.config.get("validation", {}).get("arithmetic_tolerance", 0.01)
        )
        
        # Initialize post-processing intelligence layer (Phase 3)
        post_processing_config = self.config.get("post_processing", {})
        self.post_processor = FinancialDocumentPostProcessor(
            config=post_processing_config if post_processing_config else None
        )
        self.post_processing_enabled = self.config.get("post_processing", {}).get("enabled", True)
        
        # Initialize receipt processor
        receipt_config = self.config.get("receipt_processing", {})
        self.receipt_processor = ReceiptProcessor(paddleocr_service=self.ocr_service)
        self.receipt_processing_enabled = receipt_config.get("enabled", True) if receipt_config else True
        
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
        post_processed_data = None
        
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
            
            # Step 1.4: Detect if document is a receipt and process accordingly
            receipt_data = None
            is_receipt = False
            if self.receipt_processing_enabled and ocr_results:
                try:
                    # Try to detect if this is a receipt
                    receipt_result = self.receipt_processor.process_receipt_from_ocr(ocr_results)
                    if receipt_result.get("success"):
                        is_receipt = True
                        receipt_data = receipt_result
                        logger.info(f"Detected receipt type: {receipt_result.get('receipt_type', 'unknown')}")
                except Exception as receipt_error:
                    logger.debug(f"Receipt processing attempt failed (may not be a receipt): {str(receipt_error)}")
                    # Not a receipt, continue with normal processing
            
            # Step 1.5: Apply post-processing intelligence (Phase 3) if enabled
            # Skip post-processing for receipts as they have specialized processing
            if self.post_processing_enabled and ocr_results and not is_receipt:
                logger.info("Step 1.5: Applying post-processing intelligence layer...")
                try:
                    post_processed_data = self.post_processor.process_ocr_output(ocr_results)
                    if post_processed_data.get("success"):
                        logger.info("Post-processing completed successfully")
                except Exception as pp_error:
                    logger.warning(f"Post-processing failed (non-critical): {str(pp_error)}")
                    # Continue with pipeline even if post-processing fails
            
            # Step 1.6: Generate combined JSON + Markdown output if post-processing succeeded
            markdown_output = None
            if self.post_processing_enabled and post_processed_data and post_processed_data.get("success"):
                try:
                    markdown_output = self.post_processor.generate_markdown(post_processed_data)
                    logger.info("Markdown output generated successfully")
                except Exception as md_error:
                    logger.warning(f"Markdown generation failed (non-critical): {str(md_error)}")
            
            # Step 2: Enrich with ERNIE VLM for semantic understanding
            # For receipts, we can still use VLM but with receipt-specific structure
            if is_receipt and receipt_data:
                # For receipts, use the receipt data structure
                enriched_data = {
                    "structured_data": {
                        "document_type": "receipt",
                        "receipt_type": receipt_data.get("receipt_type", "unknown"),
                        "merchant_info": receipt_data.get("data", {}).get("merchant_info", {}),
                        "transaction_info": receipt_data.get("data", {}).get("transaction_info", {}),
                        "line_items": receipt_data.get("data", {}).get("items", []),
                        "financial_summary": {
                            "subtotal": receipt_data.get("data", {}).get("totals", {}).get("subtotal", 0),
                            "tax": receipt_data.get("data", {}).get("totals", {}).get("tax", 0),
                            "discount": receipt_data.get("data", {}).get("totals", {}).get("discount", 0),
                            "grand_total": receipt_data.get("data", {}).get("totals", {}).get("total", 0),
                            "currency": "$"
                        },
                        "payment_info": receipt_data.get("data", {}).get("payment_info", {})
                    },
                    "status": "completed",
                    "model_version": "ReceiptProcessor"
                }
                logger.info("Using receipt-specific processing pipeline")
            else:
                logger.info("Step 2: Enriching with ERNIE VLM for semantic reasoning...")
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
                    
                    # Merge post-processed data if available (post-processing can supplement VLM output)
                    if post_processed_data and post_processed_data.get("success"):
                        post_structured = post_processed_data.get("data", {})
                        if post_structured:
                            # Merge vendor data (post-processing takes precedence if VLM didn't extract it)
                            if post_structured.get("vendor") and not enriched_data["structured_data"].get("vendor_block"):
                                enriched_data["structured_data"]["vendor_block"] = post_structured["vendor"]
                            # Merge client data
                            if post_structured.get("client"):
                                if not enriched_data["structured_data"].get("client_info"):
                                    enriched_data["structured_data"]["client_info"] = post_structured["client"]
                                else:
                                    # Merge client fields that might be missing
                                    client_info = enriched_data["structured_data"]["client_info"]
                                    post_client = post_structured["client"]
                                    if not client_info.get("invoice_number") and post_client.get("invoice_number"):
                                        client_info["invoice_number"] = post_client["invoice_number"]
                                    if not client_info.get("dates") and post_client.get("dates"):
                                        client_info["dates"] = post_client["dates"]
                            # Merge line items (post-processing can supplement)
                            if post_structured.get("line_items") and not enriched_data["structured_data"].get("line_items"):
                                enriched_data["structured_data"]["line_items"] = post_structured["line_items"]
                            # Merge financial summary
                            if post_structured.get("financial_summary"):
                                if not enriched_data["structured_data"].get("financial_summary"):
                                    enriched_data["structured_data"]["financial_summary"] = post_structured["financial_summary"]
                                else:
                                    # Merge financial fields
                                    summary = enriched_data["structured_data"]["financial_summary"]
                                    post_summary = post_structured["financial_summary"]
                                    for key in ["subtotal", "grand_total", "currency", "payment_terms"]:
                                        if not summary.get(key) and post_summary.get(key):
                                            summary[key] = post_summary.get(key)
                
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
                if is_receipt and receipt_data:
                    # Use receipt-specific validation
                    validation_results = receipt_data.get("validation", {
                        "is_valid": True,
                        "errors": [],
                        "warnings": []
                    })
                else:
                    # Use standard financial document validation
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
                "post_processed_data": post_processed_data if self.post_processing_enabled and not is_receipt else None,
                "receipt_data": receipt_data if is_receipt else None,  # Include receipt-specific data
                "markdown_output": markdown_output,  # Human-readable Markdown format
                "metadata": {
                    "source_file": filename,
                    "processing_timestamp": start_time.isoformat(),
                    "processing_time_ms": processing_time_ms,
                    "document_type": "receipt" if is_receipt else "invoice",
                    "receipt_type": receipt_data.get("receipt_type") if is_receipt else None,
                    "model_versions": {
                        "paddleocr_vl": ocr_results.get("model_version", "PaddleOCR-VL-0.9B") if ocr_results else "unknown",
                        "ernie_vl": enriched_data.get("model_version", "ERNIE-5") if enriched_data else "unknown",
                        "ernie_family": enriched_data.get("model_family", "unknown") if enriched_data else "unknown",
                        "receipt_processor": "ReceiptProcessor" if is_receipt else None
                    },
                    "model_type": model_type,
                    "partial_results": ocr_results.get("status") == "partial" or enriched_data.get("status") == "partial" if enriched_data else False,
                    "post_processing_enabled": self.post_processing_enabled and not is_receipt,
                    "receipt_processing_enabled": is_receipt,
                    "output_formats": ["json", "markdown"] if markdown_output else ["json"]
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
        
        # Get model name from enriched data, default to ERNIE-VLM
        model_name = enriched_data.get("model_version", "ERNIE-VLM")
        model_family = enriched_data.get("model_family", "ernie-5")
        source_model_label = f"{model_name} ({model_type})"
        
        # Handle receipt vs invoice structure
        # For receipts, merchant_info is used instead of vendor_block
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
    
    async def process_document_with_combined_output(
        self, 
        file_content: bytes, 
        filename: str, 
        model_type: str = "fine_tuned"
    ) -> Dict[str, Any]:
        """
        Process document and return both JSON and Markdown outputs simultaneously.
        This is the recommended approach for PaddleOCR-VL structured output.
        
        Args:
            file_content: Document file bytes
            filename: Original filename
            model_type: Model type to use ("fine_tuned" or "baseline")
        
        Returns:
            Dictionary with 'json' and 'markdown' keys containing structured outputs
        """
        # First get standard processing result
        standard_result = await self.process_document(file_content, filename, model_type)
        
        # If post-processing is enabled and we have OCR results, generate combined output
        if self.post_processing_enabled and standard_result.get("raw_ocr_output"):
            try:
                combined = self.post_processor.generate_combined_output(
                    standard_result.get("raw_ocr_output")
                )
                return {
                    "success": standard_result.get("success", False),
                    "document_id": standard_result.get("document_id"),
                    "status": standard_result.get("status"),
                    "json": combined.get("json", {}),
                    "markdown": combined.get("markdown", ""),
                    "metadata": {
                        **standard_result.get("metadata", {}),
                        **combined.get("metadata", {})
                    },
                    "validation": standard_result.get("validation"),
                    "extracted_data": standard_result.get("extracted_data", [])
                }
            except Exception as e:
                logger.warning(f"Failed to generate combined output: {str(e)}")
                # Fall back to standard result
                return standard_result
        
        # Fallback: return standard result with markdown if available
        return standard_result


# Global processor instance
processor = FinancialDocumentProcessor()
