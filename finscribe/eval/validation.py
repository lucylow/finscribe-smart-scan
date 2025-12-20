"""
Numeric validation for financial documents
"""

from typing import Dict, Any, Optional


def validate_totals(
    subtotal: float,
    tax: float,
    total: float,
    discount: float = 0.0,
    tolerance: float = 0.02,
) -> bool:
    """
    Validates that subtotal + tax - discount = total (within tolerance).
    
    Args:
        subtotal: Subtotal amount
        tax: Tax amount
        total: Grand total amount
        discount: Discount amount (default: 0.0)
        tolerance: Relative tolerance for comparison (default: 0.02 = 2%)
        
    Returns:
        True if validation passes, False otherwise
    """
    expected = subtotal + tax - discount
    if total == 0:
        return abs(expected) < tolerance
    
    relative_error = abs(expected - total) / max(abs(total), 1.0)
    return relative_error < tolerance


def validate_document(
    extracted: Dict[str, Any],
    tolerance: float = 0.02,
) -> Dict[str, Any]:
    """
    Validates a complete extracted financial document.
    
    Args:
        extracted: Extracted document data with totals
        tolerance: Relative tolerance for numeric validation
        
    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "errors": list of error messages,
            "warnings": list of warning messages
        }
    """
    errors = []
    warnings = []
    
    # Extract totals
    subtotal = extracted.get("subtotal", extracted.get("sub_total", 0.0))
    tax = extracted.get("tax", extracted.get("tax_total", 0.0))
    discount = extracted.get("discount", extracted.get("discount_total", 0.0))
    total = extracted.get("grand_total", extracted.get("total", 0.0))
    
    # Validate totals
    if not validate_totals(subtotal, tax, total, discount, tolerance):
        errors.append(
            f"Total mismatch: {subtotal} + {tax} - {discount} != {total}"
        )
    
    # Validate line items if present
    line_items = extracted.get("line_items", extracted.get("items", []))
    if line_items:
        calculated_subtotal = sum(
            item.get("line_total", item.get("total", 0.0))
            for item in line_items
        )
        
        if abs(calculated_subtotal - subtotal) / max(abs(subtotal), 1.0) > tolerance:
            warnings.append(
                f"Line items subtotal ({calculated_subtotal}) doesn't match "
                f"document subtotal ({subtotal})"
            )
    
    # Check for required fields
    required_fields = ["grand_total", "currency"]
    for field in required_fields:
        if field not in extracted and field.replace("_", "") not in str(extracted).lower():
            warnings.append(f"Missing recommended field: {field}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }

