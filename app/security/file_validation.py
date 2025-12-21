"""File validation utilities."""
import os
import magic
import hashlib
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Allowed file types
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
    "image/tif"
}

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}

# File size limits (in bytes)
MAX_FILE_SIZE = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024  # Default 50MB
MIN_FILE_SIZE = 100  # Minimum 100 bytes


def validate_file_size(file_content: bytes) -> Tuple[bool, Optional[str]]:
    """
    Validate file size.
    Returns: (is_valid, error_message)
    """
    file_size = len(file_content)
    
    if file_size < MIN_FILE_SIZE:
        return False, f"File too small: {file_size} bytes. Minimum: {MIN_FILE_SIZE} bytes"
    
    if file_size > MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        return False, f"File too large: {size_mb:.1f}MB. Maximum: {max_mb}MB"
    
    return True, None


def validate_file_extension(filename: str) -> Tuple[bool, Optional[str]]:
    """
    Validate file extension.
    Returns: (is_valid, error_message)
    """
    if not filename:
        return False, "Filename is required"
    
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file extension: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    
    return True, None


def validate_file_type(file_content: bytes, filename: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate file MIME type using python-magic.
    Returns: (is_valid, error_message)
    """
    try:
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_buffer(file_content)
        
        # Also check by extension as fallback
        if filename:
            ext = os.path.splitext(filename)[1].lower()
            ext_mime_map = {
                ".pdf": "application/pdf",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".tiff": "image/tiff",
                ".tif": "image/tiff"
            }
            expected_mime = ext_mime_map.get(ext)
            
            # Allow if either detected or expected matches
            if detected_mime in ALLOWED_MIME_TYPES:
                return True, None
            elif expected_mime and expected_mime in ALLOWED_MIME_TYPES:
                logger.warning(f"MIME type mismatch: detected {detected_mime}, expected {expected_mime} for {ext}")
                return True, None  # Allow if extension suggests valid type
        
        if detected_mime not in ALLOWED_MIME_TYPES:
            return False, f"Unsupported file type: {detected_mime}. Allowed: {', '.join(ALLOWED_MIME_TYPES)}"
        
        return True, None
    except Exception as e:
        logger.error(f"Error validating file type: {str(e)}")
        # If magic fails, fall back to extension check
        if filename:
            return validate_file_extension(filename)
        return False, f"Could not validate file type: {str(e)}"


def validate_file(file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
    """
    Comprehensive file validation.
    Returns: (is_valid, error_message)
    """
    # Validate extension
    is_valid, error = validate_file_extension(filename)
    if not is_valid:
        return False, error
    
    # Validate size
    is_valid, error = validate_file_size(file_content)
    if not is_valid:
        return False, error
    
    # Validate MIME type
    is_valid, error = validate_file_type(file_content, filename)
    if not is_valid:
        return False, error
    
    return True, None


def compute_file_checksum(file_content: bytes) -> str:
    """Compute SHA256 checksum of file content."""
    return hashlib.sha256(file_content).hexdigest()


