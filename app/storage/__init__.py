"""Storage module with abstraction and implementations."""
import os
import logging
from typing import Optional

from .base import StorageInterface
from .local_storage import LocalStorage
from .s3_storage import S3Storage

logger = logging.getLogger(__name__)

# Global storage instance
_storage_instance: Optional[StorageInterface] = None


def get_storage() -> StorageInterface:
    """
    Get storage instance with automatic fallback.
    
    Priority:
    1. S3/MinIO if configured (MINIO_ENDPOINT or AWS_ACCESS_KEY_ID)
    2. Local filesystem (always available)
    
    Returns:
        StorageInterface instance
    """
    global _storage_instance
    
    if _storage_instance is not None:
        return _storage_instance
    
    # Check if S3/MinIO is configured
    use_s3 = bool(
        os.getenv("MINIO_ENDPOINT") or 
        os.getenv("AWS_ACCESS_KEY_ID") or
        (os.getenv("STORAGE_TYPE", "").lower() == "s3")
    )
    
    if use_s3:
        try:
            _storage_instance = S3Storage()
            logger.info("Using S3/MinIO storage")
        except Exception as e:
            logger.warning(f"Failed to initialize S3 storage, falling back to local: {e}")
            _storage_instance = LocalStorage()
    else:
        _storage_instance = LocalStorage()
        logger.info("Using local filesystem storage")
    
    return _storage_instance


def reset_storage():
    """Reset storage instance (useful for testing)."""
    global _storage_instance
    _storage_instance = None
