"""
Extraction Service - Handles OCR and LLM extraction logic.

This service abstracts the document extraction pipeline:
1. OCR processing (PaddleOCR-VL)
2. LLM/VLM enrichment for semantic understanding
3. Post-processing intelligence layer
"""

import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..models.paddleocr_vl_service import PaddleOCRVLService
from ..models.ernie_vlm_service import ErnieVLMService
from ...config.settings import load_config
from finscribe.receipts.processor import ReceiptProcessor

logger = logging.getLogger(__name__)


class ExtractionService:
    """
    Service for extracting structured data from financial documents.
    
    Responsibilities:
    - OCR processing with PaddleOCR-VL
    - LLM/VLM semantic enrichment
    - Receipt detection and processing
    - Post-processing intelligence
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize extraction service with configuration."""
        self.config = config or load_config()
        
        # Initialize OCR service
        self.ocr_service = PaddleOCRVLService(self.config)
        
        # Initialize VLM service
        self.vlm_service = ErnieVLMService(self.config)
        
        # Initialize receipt processor
        receipt_config = self.config.get("receipt_processing", {})
        self.receipt_processor = ReceiptProcessor(paddleocr_service=self.ocr_service)
        self.receipt_processing_enabled = receipt_config.get("enabled", True) if receipt_config else True
        
        # Post-processing (if available)
        try:
            from ..post_processing.intelligence import FinancialPostProcessor as FinancialDocumentPostProcessor
            post_processing_config = self.config.get("post_processing", {})
            self.post_processor = FinancialDocumentPostProcessor(
                config=post_processing_config if post_processing_config else None
            )
            self.post_processing_enabled = self.config.get("post_processing", {}).get("enabled", True)
        except ImportError:
            logger.warning("Post-processing module not available")
            self.post_processor = None
            self.post_processing_enabled = False
    
    async def extract_from_document(
        self,
        file_content: bytes,
        filename: str,
        model_type: str = "fine_tuned"
    ) -> Dict[str, Any]:
        """
        Extract structured data from a financial document.
        
        Args:
            file_content: Raw document bytes
            filename: Original filename
            model_type: Model type to use ("fine_tuned" or "baseline")
        
        Returns:
            Dictionary containing:
            - ocr_results: Raw OCR output
            - enriched_data: LLM/VLM enriched structured data
            - receipt_data: Receipt-specific data (if applicable)
            - post_processed_data: Post-processing results (if enabled)
            - metadata: Processing metadata
        """
        document_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        logger.info(f"Extracting from document: {filename} (ID: {document_id})")
        
        # Validate inputs
        if not file_content or len(file_content) == 0:
            raise ValueError("File content is empty")
        
        ocr_results = None
        enriched_data = None
        receipt_data = None
        post_processed_data = None
        
        try:
            # Step 1: OCR Processing
            logger.info("Running OCR processing...")
            ocr_results = await self.ocr_service.parse_document(file_content)
            
            if not ocr_results or not isinstance(ocr_results, dict):
                raise ValueError("OCR service returned invalid results")
            
            if ocr_results.get("status") == "partial":
                logger.warning("OCR returned partial results - continuing with available data")
            
            # Step 2: Receipt Detection
            is_receipt = False
            if self.receipt_processing_enabled and ocr_results:
                try:
                    receipt_result = self.receipt_processor.process_receipt_from_ocr(ocr_results)
                    if receipt_result.get("success"):
                        is_receipt = True
                        receipt_data = receipt_result
                        logger.info(f"Detected receipt type: {receipt_result.get('receipt_type', 'unknown')}")
                except Exception as receipt_error:
                    logger.debug(f"Receipt processing attempt failed (may not be a receipt): {str(receipt_error)}")
            
            # Step 3: Post-processing (skip for receipts)
            if self.post_processing_enabled and ocr_results and not is_receipt and self.post_processor:
                logger.info("Applying post-processing intelligence layer...")
                try:
                    post_processed_data = self.post_processor.process_ocr_output(ocr_results)
                    if post_processed_data.get("success"):
                        logger.info("Post-processing completed successfully")
                except Exception as pp_error:
                    logger.warning(f"Post-processing failed (non-critical): {str(pp_error)}")
            
            # Step 4: LLM/VLM Enrichment
            if is_receipt and receipt_data:
                # Use receipt-specific structure
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
            else:
                logger.info("Enriching with VLM for semantic understanding...")
                try:
                    enriched_data = await self.vlm_service.enrich_financial_data(ocr_results, file_content)
                    
                    if not enriched_data or not isinstance(enriched_data, dict):
                        raise ValueError("VLM service returned invalid results")
                    
                    if enriched_data.get("status") == "partial":
                        logger.warning("VLM returned partial results - continuing with available data")
                    
                    # Ensure structured_data exists
                    if "structured_data" not in enriched_data:
                        enriched_data["structured_data"] = {}
                        logger.warning("VLM results missing structured_data - using empty structure")
                    
                    # Merge post-processed data if available
                    if post_processed_data and post_processed_data.get("success") and self.post_processor:
                        self._merge_post_processed_data(enriched_data, post_processed_data)
                
                except Exception as vlm_error:
                    logger.error(f"VLM enrichment failed: {str(vlm_error)}", exc_info=True)
                    logger.warning("Continuing with OCR results only after VLM failure")
                    enriched_data = {
                        "structured_data": {},
                        "status": "partial",
                        "error": f"VLM enrichment failed: {str(vlm_error)}"
                    }
            
            end_time = datetime.utcnow()
            processing_time_ms = (end_time - start_time).total_seconds() * 1000
            
            return {
                "success": True,
                "document_id": document_id,
                "ocr_results": ocr_results,
                "enriched_data": enriched_data,
                "receipt_data": receipt_data if is_receipt else None,
                "post_processed_data": post_processed_data if self.post_processing_enabled and not is_receipt else None,
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
                    "partial_results": ocr_results.get("status") == "partial" or (enriched_data.get("status") == "partial" if enriched_data else False),
                    "post_processing_enabled": self.post_processing_enabled and not is_receipt,
                    "receipt_processing_enabled": is_receipt
                }
            }
        
        except Exception as e:
            logger.error(f"Error extracting from document {filename} (ID: {document_id}): {str(e)}", exc_info=True)
            raise
    
    def _merge_post_processed_data(self, enriched_data: Dict[str, Any], post_processed_data: Dict[str, Any]):
        """Merge post-processed data into enriched data structure."""
        post_structured = post_processed_data.get("data", {})
        if not post_structured:
            return
        
        structured = enriched_data.get("structured_data", {})
        
        # Merge vendor data
        if post_structured.get("vendor") and not structured.get("vendor_block"):
            structured["vendor_block"] = post_structured["vendor"]
        
        # Merge client data
        if post_structured.get("client"):
            if not structured.get("client_info"):
                structured["client_info"] = post_structured["client"]
            else:
                client_info = structured["client_info"]
                post_client = post_structured["client"]
                if not client_info.get("invoice_number") and post_client.get("invoice_number"):
                    client_info["invoice_number"] = post_client["invoice_number"]
                if not client_info.get("dates") and post_client.get("dates"):
                    client_info["dates"] = post_client["dates"]
        
        # Merge line items
        if post_structured.get("line_items") and not structured.get("line_items"):
            structured["line_items"] = post_structured["line_items"]
        
        # Merge financial summary
        if post_structured.get("financial_summary"):
            if not structured.get("financial_summary"):
                structured["financial_summary"] = post_structured["financial_summary"]
            else:
                summary = structured["financial_summary"]
                post_summary = post_structured["financial_summary"]
                for key in ["subtotal", "grand_total", "currency", "payment_terms"]:
                    if not summary.get(key) and post_summary.get(key):
                        summary[key] = post_summary.get(key)

