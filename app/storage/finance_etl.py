"""
ETL Storage Model

Stores data at each stage of the ETL pipeline:
- raw_ocr/     : Raw OCR output
- parsed/      : Parsed Invoice objects
- validated/   : Validation results
- corrected/   : Human-corrected training gold data
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Base data directory
BASE = Path("data")


def store_stage(stage: str, invoice_id: str, payload: Dict[str, Any]) -> Path:
    """
    Store data at a specific ETL stage.
    
    Args:
        stage: Stage name (raw_ocr, parsed, validated, corrected)
        invoice_id: Unique invoice identifier
        payload: Data to store (will be JSON serialized)
        
    Returns:
        Path to the stored file
    """
    path = BASE / stage
    path.mkdir(parents=True, exist_ok=True)
    
    file_path = path / f"{invoice_id}.json"
    
    # Prepare data with metadata
    data = {
        "timestamp": datetime.utcnow().isoformat(),
        "invoice_id": invoice_id,
        "stage": stage,
        "data": payload
    }
    
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    
    logger.debug(f"Stored {stage} data for invoice {invoice_id} at {file_path}")
    return file_path


def load_stage(stage: str, invoice_id: str) -> Optional[Dict[str, Any]]:
    """
    Load data from a specific ETL stage.
    
    Args:
        stage: Stage name
        invoice_id: Invoice identifier
        
    Returns:
        Loaded data dictionary, or None if not found
    """
    file_path = BASE / stage / f"{invoice_id}.json"
    
    if not file_path.exists():
        return None
    
    with open(file_path, "r") as f:
        return json.load(f)


def list_invoices_in_stage(stage: str) -> list[str]:
    """
    List all invoice IDs in a stage.
    
    Args:
        stage: Stage name
        
    Returns:
        List of invoice IDs
    """
    stage_path = BASE / stage
    if not stage_path.exists():
        return []
    
    return [
        f.stem for f in stage_path.glob("*.json")
    ]


def get_etl_pipeline(invoice_id: str) -> Dict[str, Any]:
    """
    Get complete ETL pipeline data for an invoice.
    
    Args:
        invoice_id: Invoice identifier
        
    Returns:
        Dictionary with data from all stages
    """
    stages = ["raw_ocr", "parsed", "validated", "corrected"]
    pipeline_data = {}
    
    for stage in stages:
        data = load_stage(stage, invoice_id)
        if data:
            pipeline_data[stage] = data
    
    return pipeline_data

