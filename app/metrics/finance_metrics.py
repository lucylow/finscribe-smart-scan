"""
Finance Metrics Judges Care About

This powers:
- "Accuracy improved from X → Y"
- ROI justification
- One-slide results table
"""
from typing import List, Dict, Any
from decimal import Decimal
import statistics


def compute_invoice_metrics(invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute aggregate metrics for a collection of invoices.
    
    Args:
        invoices: List of invoice dictionaries with validation and confidence data
        
    Returns:
        Dictionary with computed metrics
    """
    if not invoices:
        return {
            "total_docs": 0,
            "validation_pass_rate": 0.0,
            "avg_confidence": 0.0,
            "total_value": Decimal("0"),
            "currency": "USD",
        }
    
    total = len(invoices)
    
    # Validation pass rate
    passed = sum(
        1 for i in invoices 
        if i.get("validation", {}).get("passed", False)
    )
    pass_rate = passed / total if total > 0 else 0.0
    
    # Confidence scores
    confidences = [
        i.get("confidence", 0.0) 
        for i in invoices 
        if i.get("confidence") is not None
    ]
    avg_confidence = statistics.mean(confidences) if confidences else 0.0
    min_confidence = min(confidences) if confidences else 0.0
    max_confidence = max(confidences) if confidences else 0.0
    
    # Financial totals
    total_value = Decimal("0")
    currency = "USD"
    for invoice in invoices:
        total_data = invoice.get("total", {})
        if isinstance(total_data, dict):
            value = Decimal(str(total_data.get("value", 0)))
            total_value += value
            currency = total_data.get("currency", "USD")
        elif isinstance(total_data, (int, float)):
            total_value += Decimal(str(total_data))
    
    # Error breakdown
    error_types = {}
    for invoice in invoices:
        validation = invoice.get("validation", {})
        errors = validation.get("errors", [])
        for error in errors:
            # Extract error type (first few words)
            error_type = error.split(":")[0] if ":" in error else error
            error_types[error_type] = error_types.get(error_type, 0) + 1
    
    return {
        "total_docs": total,
        "validation_pass_rate": pass_rate,
        "validation_passed": passed,
        "validation_failed": total - passed,
        "avg_confidence": round(avg_confidence, 3),
        "min_confidence": round(min_confidence, 3),
        "max_confidence": round(max_confidence, 3),
        "total_value": float(total_value),
        "currency": currency,
        "error_breakdown": error_types,
        "error_rate": (total - passed) / total if total > 0 else 0.0,
    }


def compare_metrics(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare metrics before and after improvements (e.g., fine-tuning).
    
    Args:
        before: Metrics dictionary from before
        after: Metrics dictionary from after
        
    Returns:
        Dictionary with comparison metrics
    """
    pass_rate_improvement = after["validation_pass_rate"] - before["validation_pass_rate"]
    confidence_improvement = after["avg_confidence"] - before["avg_confidence"]
    
    return {
        "pass_rate_improvement": round(pass_rate_improvement, 3),
        "pass_rate_improvement_pct": round(
            (pass_rate_improvement / before["validation_pass_rate"] * 100) 
            if before["validation_pass_rate"] > 0 else 0, 
            1
        ),
        "confidence_improvement": round(confidence_improvement, 3),
        "error_rate_reduction": round(
            before["error_rate"] - after["error_rate"], 
            3
        ),
        "before": before,
        "after": after,
    }

