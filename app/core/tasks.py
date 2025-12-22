"""
Celery tasks for asynchronous document processing.

This module defines background tasks for:
- Document processing (OCR + LLM + Validation)
- Active learning data export
- Batch processing
"""

import logging
from typing import Dict, Any, Optional
from celery import Task

from .celery_app import celery_app
from .services import ExtractionService, ValidationService, ActiveLearningService
from .document_processor import FinancialDocumentProcessor
from ..config.settings import load_config

logger = logging.getLogger(__name__)

# Initialize services
config = load_config()
extraction_service = ExtractionService(config)
validation_service = ValidationService(config)
active_learning_service = ActiveLearningService(config)
processor = FinancialDocumentProcessor(config)


@celery_app.task(bind=True, name="process_document")
def process_document_task(
    self: Task,
    job_id: str,
    file_content: bytes,
    filename: str,
    model_type: str = "fine_tuned"
) -> Dict[str, Any]:
    """
    Process a document asynchronously.
    
    Args:
        job_id: Unique job identifier
        file_content: Raw document bytes
        filename: Original filename
        model_type: Model type to use
    
    Returns:
        Processing result dictionary
    """
    try:
        logger.info(f"Starting document processing task for job {job_id}")
        
        # Update job status to processing
        # TODO: Integrate with job_manager
        
        # Process document
        result = processor.process_document(file_content, filename, model_type)
        
        if result.get("success"):
            # Log to active learning if needed
            enriched_data = result.get("structured_output", {})
            validation = result.get("validation", {})
            
            if validation.get("needs_review", False):
                active_learning_service.log_extraction(
                    document_id=result.get("document_id"),
                    filename=filename,
                    enriched_data={"structured_data": enriched_data},
                    validation=validation,
                    model_type=model_type
                )
            
            logger.info(f"Document processing completed for job {job_id}")
            return {
                "success": True,
                "job_id": job_id,
                "result": result
            }
        else:
            logger.error(f"Document processing failed for job {job_id}: {result.get('error')}")
            return {
                "success": False,
                "job_id": job_id,
                "error": result.get("error")
            }
    
    except Exception as e:
        logger.error(f"Error in document processing task for job {job_id}: {str(e)}", exc_info=True)
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(name="export_active_learning")
def export_active_learning_task(limit: Optional[int] = None) -> list:
    """
    Export active learning data for training.
    
    Args:
        limit: Optional limit on number of records
    
    Returns:
        List of training records
    """
    try:
        logger.info(f"Exporting active learning data (limit: {limit})")
        records = active_learning_service.export_for_training(limit=limit)
        logger.info(f"Exported {len(records)} active learning records")
        return records
    except Exception as e:
        logger.error(f"Error exporting active learning data: {str(e)}", exc_info=True)
        raise
