"""
Automatic error classification for hard-sample mining
"""

from typing import Dict, Any


def classify_error(pred: Dict[str, Any], gt: Dict[str, Any]) -> str:
    """
    Classifies the type of error in a prediction.
    
    Args:
        pred: Predicted data
        gt: Ground truth data
        
    Returns:
        Error type string
    """
    # Check for total mismatch
    pred_total = pred.get("grand_total", pred.get("total", 0.0))
    gt_total = gt.get("grand_total", gt.get("total", 0.0))
    
    if abs(pred_total - gt_total) > 0.02 * max(abs(gt_total), 1.0):
        return "TOTAL_MISMATCH"
    
    # Check for table structure errors
    pred_items = pred.get("line_items", pred.get("items", []))
    gt_items = gt.get("line_items", gt.get("items", []))
    
    if len(pred_items) != len(gt_items):
        return "TABLE_STRUCTURE_ERROR"
    
    # Check for currency mismatch
    pred_currency = pred.get("currency", "").upper()
    gt_currency = gt.get("currency", "").upper()
    
    if pred_currency and gt_currency and pred_currency != gt_currency:
        return "CURRENCY_ERROR"
    
    # Check for date format errors
    pred_date = pred.get("issue_date", pred.get("date", ""))
    gt_date = gt.get("issue_date", gt.get("date", ""))
    
    if pred_date and gt_date and pred_date != gt_date:
        return "DATE_ERROR"
    
    # Check for vendor/client info errors
    pred_vendor = pred.get("vendor_name", pred.get("vendor", {}).get("name", ""))
    gt_vendor = gt.get("vendor_name", gt.get("vendor", {}).get("name", ""))
    
    if pred_vendor and gt_vendor and pred_vendor.lower() != gt_vendor.lower():
        return "VENDOR_INFO_ERROR"
    
    # Default to other
    return "OTHER"


def get_error_severity(error_type: str) -> int:
    """
    Returns error severity (1-5, higher = more severe).
    
    Args:
        error_type: Error type string
        
    Returns:
        Severity score
    """
    severity_map = {
        "TOTAL_MISMATCH": 5,
        "TABLE_STRUCTURE_ERROR": 4,
        "CURRENCY_ERROR": 3,
        "DATE_ERROR": 2,
        "VENDOR_INFO_ERROR": 2,
        "OTHER": 1,
    }
    return severity_map.get(error_type, 1)

