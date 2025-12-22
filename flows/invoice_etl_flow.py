"""
Prefect Flow for FinScribe Invoice ETL Pipeline

This flow orchestrates the complete ETL pipeline with:
- Automatic retries
- Caching for idempotency
- Comprehensive logging
- Optional Slack notifications
"""
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from datetime import timedelta
from typing import Dict, Any

from data_pipeline.ingestion import ingest_from_local, ingest_from_bytes
from data_pipeline.preprocess import preprocess
from data_pipeline.ocr_client import run_ocr
from data_pipeline.semantic_parser import parse
from data_pipeline.normalizer import normalize_invoice_data
from data_pipeline.validator import validate
from data_pipeline.persistence import save_invoice


# -----------------------
# TASK DEFINITIONS
# -----------------------

@task(
    retries=3,
    retry_delay_seconds=10,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=12),
    name="ingest_file"
)
def ingest(path: str) -> str:
    """
    Ingest file from local path.
    
    Args:
        path: Path to invoice file
        
    Returns:
        Path to ingested file
    """
    logger = get_run_logger()
    logger.info(f"Ingesting file: {path}")
    result = ingest_from_local(path)
    logger.info(f"Ingestion complete: {result}")
    return result


@task(
    retries=2,
    retry_delay_seconds=5,
    name="preprocess_image"
)
def preprocess_image(path: str, enable_denoise: bool = False) -> str:
    """
    Preprocess image for OCR.
    
    Args:
        path: Path to image file
        enable_denoise: Whether to enable denoising
        
    Returns:
        Path to preprocessed image
    """
    logger = get_run_logger()
    logger.info(f"Preprocessing image: {path}")
    result = preprocess(path, enable_denoise=enable_denoise)
    logger.info(f"Preprocessing complete: {result}")
    return result


@task(
    retries=2,
    retry_delay_seconds=10,
    name="run_ocr"
)
def ocr(path: str) -> Dict[str, Any]:
    """
    Run OCR on preprocessed image.
    
    Args:
        path: Path to preprocessed image
        
    Returns:
        OCR results dictionary
    """
    logger = get_run_logger()
    logger.info(f"Running OCR: {path}")
    result = run_ocr(path)
    logger.info(f"OCR complete. Confidence: {result.get('confidence', 0.0):.2f}")
    return result


@task(
    retries=1,
    name="semantic_parse"
)
def semantic_parse(ocr_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse OCR output to structured fields.
    
    Args:
        ocr_json: OCR results dictionary
        
    Returns:
        Structured invoice data
    """
    logger = get_run_logger()
    logger.info("Parsing semantic structure")
    result = parse(ocr_json)
    logger.info(f"Parsing complete. Invoice number: {result.get('invoice_number', 'N/A')}")
    return result


@task(
    name="normalize_data"
)
def normalize_data(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize invoice data.
    
    Args:
        parsed: Parsed invoice data
        
    Returns:
        Normalized invoice data
    """
    logger = get_run_logger()
    logger.info("Normalizing data")
    result = normalize_invoice_data(parsed)
    logger.info("Normalization complete")
    return result


@task(
    name="validate_data"
)
def validate_data(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate invoice data.
    
    Args:
        parsed: Parsed invoice data
        
    Returns:
        Validation results
    """
    logger = get_run_logger()
    logger.info("Validating data")
    result = validate(parsed)
    if result["ok"]:
        logger.info("Validation passed")
    else:
        logger.warning(f"Validation failed: {result['errors']}")
    return result


@task(
    retries=2,
    retry_delay_seconds=5,
    name="persist_invoice"
)
def persist_invoice(
    parsed: Dict[str, Any],
    raw_ocr: Dict[str, Any],
    source: str
) -> int:
    """
    Persist invoice to database.
    
    Args:
        parsed: Parsed invoice data
        raw_ocr: Raw OCR output
        source: Source file path
        
    Returns:
        Invoice ID
    """
    logger = get_run_logger()
    logger.info("Persisting invoice")
    inv_id = save_invoice(parsed, raw_ocr, source)
    logger.info(f"Persisted invoice ID: {inv_id}")
    return inv_id


# -----------------------
# FLOW
# -----------------------

@flow(
    name="FinScribe Invoice ETL",
    retries=1,
    retry_delay_seconds=30,
    log_prints=True
)
def invoice_etl_flow(
    invoice_path: str,
    enable_denoise: bool = False
) -> Dict[str, Any]:
    """
    Complete ETL pipeline for invoice processing.
    
    Args:
        invoice_path: Path to invoice file
        enable_denoise: Whether to enable denoising
        
    Returns:
        Dictionary with invoice_id, validation results, and status
    """
    logger = get_run_logger()
    logger.info(f"Starting ETL pipeline for {invoice_path}")

    # Extract
    src = ingest(invoice_path)
    clean = preprocess_image(src, enable_denoise=enable_denoise)
    ocr_json = ocr(clean)
    
    # Transform
    parsed = semantic_parse(ocr_json)
    normalized = normalize_data(parsed)
    
    # Validate
    validation = validate_data(normalized)
    
    # Load
    invoice_id = persist_invoice(normalized, ocr_json, src)

    logger.info(f"ETL pipeline completed successfully. Invoice ID: {invoice_id}")
    logger.info(f"Validation: {'PASSED' if validation['ok'] else 'FAILED'}")

    return {
        "invoice_id": invoice_id,
        "validation": validation,
        "status": "success"
    }


# -----------------------
# NOTIFICATION SETUP (Optional)
# -----------------------

def setup_slack_notifications():
    """
    Setup Slack notifications for flow failures.
    
    Requires: pip install prefect-slack
    
    Usage:
        from prefect_slack import SlackWebhook
        slack = SlackWebhook.load("finscribe-slack")
        
        @flow(on_failure=[slack.notify])
        def invoice_etl_flow(...):
            ...
    """
    try:
        from prefect_slack import SlackWebhook
        return SlackWebhook
    except ImportError:
        print("prefect-slack not installed. Install with: pip install prefect-slack")
        return None


if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) > 1:
        invoice_path = sys.argv[1]
    else:
        invoice_path = "examples/sample_invoice_1.png"
    
    result = invoice_etl_flow(invoice_path)
    print(f"Result: {result}")

