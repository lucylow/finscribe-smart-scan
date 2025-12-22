"""
Pydantic schemas for FinScribe data contracts.

These schemas ensure type safety and data validation across the application.
All API request/response models should inherit from these base schemas.
"""

from .extraction import (
    ExtractedField,
    LineItem,
    FinancialSummary,
    VendorInfo,
    ClientInfo,
    ExtractedDocument,
    ExtractionResult,
)
from .validation import (
    ValidationResult,
    ValidationIssue,
)
from .job import (
    JobStatus,
    JobResponse,
    JobStatusResponse,
)

__all__ = [
    # Extraction schemas
    "ExtractedField",
    "LineItem",
    "FinancialSummary",
    "VendorInfo",
    "ClientInfo",
    "ExtractedDocument",
    "ExtractionResult",
    # Validation schemas
    "ValidationResult",
    "ValidationIssue",
    # Job schemas
    "JobStatus",
    "JobResponse",
    "JobStatusResponse",
]

