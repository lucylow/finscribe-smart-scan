"""
Field extraction accuracy metrics
"""

from typing import Dict, Any


def field_accuracy(pred: Dict[str, Any], gt: Dict[str, Any]) -> float:
    """
    Calculates field extraction accuracy by comparing predicted and ground truth fields.
    
    Args:
        pred: Predicted field dictionary
        gt: Ground truth field dictionary
        
    Returns:
        Accuracy score between 0.0 and 1.0
    """
    if not gt:
        return 0.0
    
    correct = 0
    total = 0
    
    for key, value in gt.items():
        total += 1
        pred_value = pred.get(key)
        
        # Normalize values for comparison
        pred_str = str(pred_value).strip().lower() if pred_value is not None else ""
        gt_str = str(value).strip().lower()
        
        # Exact match
        if pred_str == gt_str:
            correct += 1
        # Numeric comparison with tolerance
        elif _is_numeric(pred_str) and _is_numeric(gt_str):
            try:
                pred_num = float(pred_str)
                gt_num = float(gt_str)
                # Allow 0.01% tolerance for floating point
                if abs(pred_num - gt_num) / max(abs(gt_num), 1.0) < 0.0001:
                    correct += 1
            except ValueError:
                pass
    
    return correct / max(total, 1)


def _is_numeric(s: str) -> bool:
    """Check if string represents a number."""
    try:
        float(s)
        return True
    except ValueError:
        return False


def field_f1_score(pred: Dict[str, Any], gt: Dict[str, Any]) -> float:
    """
    Calculates F1 score for field extraction.
    
    Args:
        pred: Predicted field dictionary
        gt: Ground truth field dictionary
        
    Returns:
        F1 score between 0.0 and 1.0
    """
    if not gt:
        return 0.0
    
    tp = 0  # True positives
    fp = 0  # False positives
    fn = 0  # False negatives
    
    # Check ground truth fields
    for key, value in gt.items():
        pred_value = pred.get(key)
        pred_str = str(pred_value).strip().lower() if pred_value is not None else ""
        gt_str = str(value).strip().lower()
        
        if pred_str == gt_str:
            tp += 1
        else:
            fn += 1
    
    # Check for extra predicted fields
    for key in pred:
        if key not in gt:
            fp += 1
    
    # Calculate F1
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * (precision * recall) / max(precision + recall, 1e-10)
    
    return f1

