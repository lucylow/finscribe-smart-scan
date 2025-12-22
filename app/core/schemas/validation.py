"""
Pydantic schemas for validation results.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ValidationIssue(BaseModel):
    """A single validation issue."""
    
    field: Optional[str] = Field(None, description="Field name (if applicable)")
    issue_type: str = Field(..., description="Type of issue (arithmetic, date, required, etc.)")
    message: str = Field(..., description="Human-readable error message")
    severity: str = Field(default="error", description="Severity level (error, warning)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "grand_total",
                "issue_type": "arithmetic",
                "message": "Grand total (1650.0) does not match subtotal + tax (1650.0)",
                "severity": "error"
            }
        }
    )


class ValidationResult(BaseModel):
    """Complete validation result."""
    
    is_valid: bool = Field(..., description="Whether validation passed")
    math_ok: bool = Field(..., description="Whether arithmetic checks passed")
    dates_ok: bool = Field(..., description="Whether date logic checks passed")
    issues: List[ValidationIssue] = Field(default_factory=list, description="List of validation issues")
    field_confidences: Dict[str, float] = Field(
        default_factory=dict,
        description="Confidence scores per field"
    )
    needs_review: bool = Field(default=False, description="Whether human review is needed")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Overall confidence score")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_valid": True,
                "math_ok": True,
                "dates_ok": True,
                "issues": [],
                "field_confidences": {
                    "vendor_name": 0.98,
                    "grand_total": 0.97
                },
                "needs_review": False,
                "confidence": 0.96
            }
        }
    )

