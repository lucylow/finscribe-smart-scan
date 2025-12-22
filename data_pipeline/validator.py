"""
Data validation module for business rule checking.

Validates:
- Arithmetic correctness (subtotal + tax = total)
- Required fields presence
- Data type consistency
- Business logic rules
"""
import logging
from typing import Dict, Any, List

LOG = logging.getLogger("validator")


def check_arithmetic(parsed: Dict[str, Any], tolerance: float = 0.01) -> Dict[str, Any]:
    """
    Validate arithmetic correctness of financial data.
    
    Args:
        parsed: Parsed invoice data
        tolerance: Allowed difference for floating point comparison
        
    Returns:
        Validation result dictionary with 'ok' and 'errors' fields
    """
    out = {"ok": True, "errors": []}
    
    fs = parsed.get("financial_summary", {})
    line_items = parsed.get("line_items", [])
    
    # Check line items sum
    if line_items:
        calculated_subtotal = sum([
            item.get("line_total", 0.0) or 0.0
            for item in line_items
        ])
        
        stated_subtotal = fs.get("subtotal", 0.0) or 0.0
        tax = fs.get("tax", 0.0) or 0.0
        grand_total = fs.get("grand_total", 0.0) or 0.0
        
        # Check subtotal
        if stated_subtotal > 0 and abs(calculated_subtotal - stated_subtotal) > tolerance:
            out["ok"] = False
            out["errors"].append(
                f"Line items sum ({calculated_subtotal:.2f}) != stated subtotal ({stated_subtotal:.2f})"
            )
        
        # Check grand total
        calculated_total = stated_subtotal + tax
        if grand_total > 0 and abs(calculated_total - grand_total) > tolerance:
            out["ok"] = False
            out["errors"].append(
                f"Subtotal + tax ({calculated_total:.2f}) != grand total ({grand_total:.2f})"
            )
    
    return out


def check_required_fields(parsed: Dict[str, Any], required: List[str] = None) -> Dict[str, Any]:
    """
    Check that required fields are present.
    
    Args:
        parsed: Parsed invoice data
        required: List of required field paths (e.g., ["invoice_number", "financial_summary.grand_total"])
        
    Returns:
        Validation result dictionary
    """
    if required is None:
        required = ["invoice_number", "financial_summary.grand_total"]
    
    out = {"ok": True, "errors": []}
    
    for field_path in required:
        parts = field_path.split(".")
        value = parsed
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break
        
        if not value:
            out["ok"] = False
            out["errors"].append(f"Missing required field: {field_path}")
    
    return out


def check_data_types(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate data types are correct.
    
    Args:
        parsed: Parsed invoice data
        
    Returns:
        Validation result dictionary
    """
    out = {"ok": True, "errors": []}
    
    # Check financial summary types
    fs = parsed.get("financial_summary", {})
    for key in ["subtotal", "tax", "grand_total"]:
        if key in fs:
            value = fs[key]
            if not isinstance(value, (int, float)):
                out["ok"] = False
                out["errors"].append(f"financial_summary.{key} must be numeric, got {type(value).__name__}")
    
    # Check line items
    line_items = parsed.get("line_items", [])
    if not isinstance(line_items, list):
        out["ok"] = False
        out["errors"].append("line_items must be a list")
    else:
        for i, item in enumerate(line_items):
            if not isinstance(item, dict):
                out["ok"] = False
                out["errors"].append(f"line_items[{i}] must be a dictionary")
                continue
            
            for field in ["unit_price", "line_total"]:
                if field in item:
                    value = item[field]
                    if not isinstance(value, (int, float)):
                        out["ok"] = False
                        out["errors"].append(f"line_items[{i}].{field} must be numeric, got {type(value).__name__}")
    
    return out


def validate(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run all validation checks.
    
    Args:
        parsed: Parsed invoice data
        
    Returns:
        Combined validation result dictionary
    """
    results = {
        "ok": True,
        "errors": [],
        "checks": {}
    }
    
    # Run all checks
    arithmetic = check_arithmetic(parsed)
    required = check_required_fields(parsed)
    types = check_data_types(parsed)
    
    results["checks"] = {
        "arithmetic": arithmetic,
        "required_fields": required,
        "data_types": types
    }
    
    # Aggregate errors
    for check_result in [arithmetic, required, types]:
        if not check_result["ok"]:
            results["ok"] = False
            results["errors"].extend(check_result["errors"])
    
    if results["ok"]:
        LOG.info("Validation passed")
    else:
        LOG.warning(f"Validation failed: {results['errors']}")
    
    return results

