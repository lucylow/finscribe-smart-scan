"""
Validation & Reconciliation Engine

Key differentiator: Deterministic validation with math + business rules.
Enables automatic rejection / human-review routing, validation pass-rate metrics,
and before/after fine-tune comparison.
"""
from app.models.finance import Invoice
from decimal import Decimal
from typing import List


class ValidationResult:
    """Result of invoice validation."""
    
    def __init__(self):
        self.passed = True
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def fail(self, msg: str):
        """Record a validation failure."""
        self.passed = False
        self.errors.append(msg)
    
    def warn(self, msg: str):
        """Record a validation warning (non-fatal)."""
        self.warnings.append(msg)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_invoice(invoice: Invoice) -> ValidationResult:
    """
    Validate invoice with math and business rules.
    
    Args:
        invoice: Invoice object to validate
        
    Returns:
        ValidationResult with pass/fail status and any errors
    """
    result = ValidationResult()
    
    # Pydantic model validation (math checks are already in the model)
    try:
        # This will raise ValidationError if model validation fails
        _ = invoice.model_dump()
    except Exception as e:
        result.fail(f"Model validation failed: {str(e)}")
        return result  # Early return if model is invalid
    
    # Additional line-item sum check (redundant but explicit)
    line_sum = sum(li.total.value for li in invoice.line_items)
    if abs(line_sum - invoice.subtotal.value) > Decimal("0.02"):
        result.fail(
            f"Line items do not sum to subtotal: "
            f"line items sum to {line_sum}, subtotal is {invoice.subtotal.value}"
        )
    
    # Check for empty line items
    if len(invoice.line_items) == 0:
        result.warn("Invoice has no line items")
    
    # Check confidence threshold
    if invoice.confidence is not None and invoice.confidence < 0.7:
        result.warn(f"Low confidence score: {invoice.confidence:.2f}")
    
    # Check for negative amounts (business rule)
    if invoice.subtotal.value < 0:
        result.fail("Subtotal cannot be negative")
    if invoice.total.value < 0:
        result.fail("Total cannot be negative")
    for li in invoice.line_items:
        if li.total.value < 0:
            result.fail(f"Line item '{li.description}' has negative total")
    
    return result

