"""ETL storage utilities"""
import json
import os
from pathlib import Path
from typing import Any, Dict
from datetime import datetime


def ensure_data_dir(stage: str) -> Path:
    """Ensure data directory exists for a stage"""
    data_dir = Path("data") / stage
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def store_stage(stage: str, invoice_id: str, payload: Dict[str, Any]) -> str:
    """
    Store a pipeline stage result to disk.
    
    Args:
        stage: Stage name (e.g., 'ocr', 'parsed', 'validated')
        invoice_id: Unique invoice identifier
        payload: Data to store
        
    Returns:
        Path to stored file
    """
    data_dir = ensure_data_dir(stage)
    timestamp = datetime.utcnow().isoformat()
    
    # Add metadata
    payload_with_meta = {
        "invoice_id": invoice_id,
        "stage": stage,
        "timestamp": timestamp,
        "data": payload
    }
    
    file_path = data_dir / f"{invoice_id}.json"
    
    with open(file_path, "w") as f:
        json.dump(payload_with_meta, f, indent=2, default=str)
    
    return str(file_path)


def load_stage(stage: str, invoice_id: str) -> Dict[str, Any]:
    """Load a stored stage result"""
    data_dir = Path("data") / stage
    file_path = data_dir / f"{invoice_id}.json"
    
    if not file_path.exists():
        raise FileNotFoundError(f"Stage file not found: {file_path}")
    
    with open(file_path, "r") as f:
        return json.load(f)
