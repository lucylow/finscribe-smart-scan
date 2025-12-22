"""
Utility functions for ETL pipeline.
"""
import uuid
import os
from datetime import datetime
from typing import Any, Optional

def generate_id(prefix: str = "inv") -> str:
    """
    Generate a unique ID with optional prefix.
    
    Args:
        prefix: ID prefix
        
    Returns:
        Unique ID string
    """
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def safe_cast(x: Any, typ: type, default: Optional[Any] = None) -> Any:
    """
    Safely cast value to type, returning default on failure.
    
    Args:
        x: Value to cast
        typ: Target type
        default: Default value if cast fails
        
    Returns:
        Cast value or default
    """
    try:
        return typ(x)
    except (ValueError, TypeError):
        return default


def timestamp() -> str:
    """
    Get current UTC timestamp in ISO format.
    
    Returns:
        ISO format timestamp string
    """
    return datetime.utcnow().isoformat() + "Z"


def ensure_dir(path: str) -> str:
    """
    Ensure directory exists, create if not.
    
    Args:
        path: Directory path
        
    Returns:
        Path string
    """
    os.makedirs(path, exist_ok=True)
    return path

