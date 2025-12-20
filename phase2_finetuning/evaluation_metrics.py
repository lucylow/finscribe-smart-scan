"""
Phase 2: Evaluation Metrics for Fine-Tuned PaddleOCR-VL

Implements region-specific evaluation metrics:
1. Field Extraction Accuracy (per region)
2. Table Structure Accuracy (TEDS - Table Extraction Dataset Score)
3. Numerical Validation (mathematical consistency checks)
"""

import json
import re
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict
import numpy as np


def extract_region_content(response: Dict[str, Any], region: str) -> Optional[Dict[str, Any]]:
    """
    Extract content for a specific region from model response.
    
    Args:
        response: Parsed JSON response from model
        region: Region name (e.g., "vendor_block", "line_item_table")
        
    Returns:
        Content dictionary for the region, or None if not found
    """
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            return None
    
    if response.get('region') == region:
        return response.get('content')
    
    # Handle nested structures
    if 'content' in response:
        content = response['content']
        if isinstance(content, dict) and region in content:
            return content[region]
    
    return None


def field_extraction_accuracy(
    predicted: Dict[str, Any],
    ground_truth: Dict[str, Any],
    region: str
) -> Tuple[float, Dict[str, bool]]:
    """
    Calculate field extraction accuracy for a specific region.
    
    Args:
        predicted: Predicted response dictionary
        ground_truth: Ground truth metadata dictionary
        region: Region name to evaluate
        
    Returns:
        Tuple of (overall_accuracy, field_accuracy_dict)
    """
    pred_content = extract_region_content(predicted, region)
    if pred_content is None:
        return 0.0, {}
    
    # Map region names to ground truth paths
    region_mapping = {
        "vendor_block": ("vendor", {}),
        "client_invoice_info": (None, {
            "invoice_number": "invoice_id",
            "issue_date": "issue_date",
            "due_date": "due_date",
            "client": ("client", "name")
        }),
        "financial_summary": (None, {
            "subtotal": "subtotal",
            "tax_total": "tax_total",
            "discount_total": "discount_total",
            "grand_total": "grand_total",
            "payment_terms": "payment_terms",
            "currency": "currency"
        })
    }
    
    if region == "vendor_block":
        gt_vendor = ground_truth.get('vendor', {})
        field_accuracy = {}
        
        # Check name
        pred_name = pred_content.get('name', '').strip().lower()
        gt_name = gt_vendor.get('name', '').strip().lower()
        field_accuracy['name'] = pred_name == gt_name
        
        # Check address (partial match is acceptable)
        pred_address = pred_content.get('address', '').strip().lower()
        gt_address = f"{gt_vendor.get('address', '')}, {gt_vendor.get('city', '')}, {gt_vendor.get('country', '')} {gt_vendor.get('postal_code', '')}".strip().lower()
        # Simple token-based matching for addresses
        pred_tokens = set(pred_address.split())
        gt_tokens = set(gt_address.split())
        field_accuracy['address'] = len(pred_tokens & gt_tokens) / max(len(gt_tokens), 1) > 0.7
        
        # Check contact info
        pred_contact = pred_content.get('contact', '').lower()
        gt_phone = gt_vendor.get('phone', '').lower()
        gt_email = gt_vendor.get('email', '').lower()
        gt_tax_id = gt_vendor.get('tax_id', '').lower()
        field_accuracy['contact'] = (
            gt_phone in pred_contact or 
            gt_email in pred_contact or 
            gt_tax_id in pred_contact
        )
        
        overall = sum(field_accuracy.values()) / len(field_accuracy)
        return overall, field_accuracy
    
    elif region == "client_invoice_info":
        field_accuracy = {}
        mapping = region_mapping[region][1]
        
        for pred_key, gt_path in mapping.items():
            pred_value = str(pred_content.get(pred_key, '')).strip().lower()
            
            if isinstance(gt_path, tuple):
                # Nested path
                gt_value = str(ground_truth.get(gt_path[0], {}).get(gt_path[1], '')).strip().lower()
            else:
                gt_value = str(ground_truth.get(gt_path, '')).strip().lower()
            
            field_accuracy[pred_key] = pred_value == gt_value
        
        overall = sum(field_accuracy.values()) / len(field_accuracy) if field_accuracy else 0.0
        return overall, field_accuracy
    
    elif region == "financial_summary":
        field_accuracy = {}
        mapping = region_mapping[region][1]
        
        for pred_key, gt_path in mapping.items():
            if pred_key == "currency":
                pred_value = str(pred_content.get(pred_key, '')).strip().upper()
                gt_value = str(ground_truth.get(gt_path, '')).strip().upper()
                field_accuracy[pred_key] = pred_value == gt_value
            elif pred_key == "payment_terms":
                pred_value = str(pred_content.get(pred_key, '')).strip().lower()
                gt_value = str(ground_truth.get(gt_path, '')).strip().lower()
                # Fuzzy matching for payment terms
                field_accuracy[pred_key] = pred_value == gt_value or len(set(pred_value.split()) & set(gt_value.split())) / max(len(gt_value.split()), 1) > 0.7
            else:
                # Numerical fields - allow small tolerance
                pred_value = float(pred_content.get(pred_key, 0))
                gt_value = float(ground_truth.get(gt_path, 0))
                field_accuracy[pred_key] = abs(pred_value - gt_value) < 0.01
        
        overall = sum(field_accuracy.values()) / len(field_accuracy) if field_accuracy else 0.0
        return overall, field_accuracy
    
    return 0.0, {}


def table_structure_accuracy(
    predicted: List[Dict[str, Any]],
    ground_truth: List[Dict[str, Any]]
) -> Tuple[float, Dict[str, float]]:
    """
    Calculate Table Extraction Dataset Score (TEDS) for line item tables.
    
    This evaluates:
    1. Correct number of rows
    2. Correct structure (columns present)
    3. Cell-level accuracy
    
    Args:
        predicted: Predicted line items list
        ground_truth: Ground truth items list
        
    Returns:
        Tuple of (overall_TEDS_score, detailed_metrics)
    """
    if not predicted and not ground_truth:
        return 1.0, {"row_count_match": 1.0, "column_match": 1.0, "cell_accuracy": 1.0}
    
    if not predicted or not ground_truth:
        return 0.0, {"row_count_match": 0.0, "column_match": 0.0, "cell_accuracy": 0.0}
    
    # Row count accuracy
    pred_rows = len(predicted)
    gt_rows = len(ground_truth)
    row_count_match = 1.0 if pred_rows == gt_rows else max(0.0, 1.0 - abs(pred_rows - gt_rows) / max(gt_rows, 1))
    
    # Column structure accuracy
    required_columns = {"description", "quantity", "unit_price", "line_total"}
    pred_columns = set()
    if predicted:
        pred_columns = set(predicted[0].keys())
    column_match = len(required_columns & pred_columns) / len(required_columns) if required_columns else 1.0
    
    # Cell-level accuracy
    min_rows = min(len(predicted), len(ground_truth))
    cell_correct = 0
    cell_total = 0
    
    for i in range(min_rows):
        pred_item = predicted[i]
        gt_item = ground_truth[i]
        
        for col in required_columns:
            cell_total += 1
            if col in pred_item and col in gt_item:
                pred_val = pred_item[col]
                gt_val = gt_item[col]
                
                if col == "description":
                    # Text matching - use token-based similarity
                    pred_tokens = set(str(pred_val).lower().split())
                    gt_tokens = set(str(gt_val).lower().split())
                    if pred_tokens and gt_tokens:
                        similarity = len(pred_tokens & gt_tokens) / len(pred_tokens | gt_tokens)
                        if similarity > 0.7:
                            cell_correct += 1
                else:
                    # Numerical matching
                    try:
                        pred_num = float(pred_val)
                        gt_num = float(gt_val)
                        if abs(pred_num - gt_num) < 0.01:
                            cell_correct += 1
                    except (ValueError, TypeError):
                        pass
    
    cell_accuracy = cell_correct / cell_total if cell_total > 0 else 0.0
    
    # Overall TEDS score (weighted combination)
    teds_score = 0.4 * row_count_match + 0.3 * column_match + 0.3 * cell_accuracy
    
    metrics = {
        "row_count_match": row_count_match,
        "column_match": column_match,
        "cell_accuracy": cell_accuracy,
        "teds_score": teds_score
    }
    
    return teds_score, metrics


def numerical_validation(predicted: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate mathematical consistency of extracted financial data.
    
    Checks:
    - subtotal + tax_total - discount_total ≈ grand_total
    
    Args:
        predicted: Predicted response dictionary (should contain financial_summary)
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    financial_content = extract_region_content(predicted, "financial_summary")
    if not financial_content:
        return False, ["Financial summary not found in prediction"]
    
    try:
        subtotal = float(financial_content.get('subtotal', 0))
        tax_total = float(financial_content.get('tax_total', 0))
        discount_total = float(financial_content.get('discount_total', 0))
        grand_total = float(financial_content.get('grand_total', 0))
        
        calculated_total = subtotal + tax_total - discount_total
        difference = abs(calculated_total - grand_total)
        
        # Allow small floating point errors
        if difference > 0.01:
            errors.append(
                f"Grand total mismatch: calculated {calculated_total:.2f}, "
                f"reported {grand_total:.2f}, difference {difference:.2f}"
            )
        
        # Validate line items sum to subtotal (if available)
        table_content = extract_region_content(predicted, "line_item_table")
        if table_content and isinstance(table_content, list):
            item_totals = [float(item.get('line_total', 0)) for item in table_content]
            items_sum = sum(item_totals)
            
            # Note: items_sum might include tax/discount per item, so this is approximate
            # In a full implementation, you'd need to track item-level calculations
            if abs(items_sum - subtotal) > 1.0:  # Larger tolerance for item-level sums
                errors.append(
                    f"Line items sum ({items_sum:.2f}) doesn't match subtotal ({subtotal:.2f})"
                )
        
    except (ValueError, TypeError) as e:
        errors.append(f"Error parsing numerical values: {e}")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def evaluate_sample(
    predicted_response: str,
    ground_truth: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Comprehensive evaluation for a single invoice sample.
    
    Args:
        predicted_response: JSON string response from model
        ground_truth: Ground truth metadata dictionary
        
    Returns:
        Dictionary with evaluation results
    """
    try:
        predicted = json.loads(predicted_response) if isinstance(predicted_response, str) else predicted_response
    except json.JSONDecodeError:
        return {
            "error": "Failed to parse predicted response as JSON",
            "field_extraction": {},
            "table_accuracy": 0.0,
            "numerical_validation": False
        }
    
    results = {
        "field_extraction": {},
        "table_accuracy": {},
        "numerical_validation": {}
    }
    
    # Evaluate each region
    regions = ["vendor_block", "client_invoice_info", "financial_summary"]
    for region in regions:
        accuracy, field_acc = field_extraction_accuracy(predicted, ground_truth, region)
        results["field_extraction"][region] = {
            "overall_accuracy": accuracy,
            "field_details": field_acc
        }
    
    # Evaluate table structure
    pred_table = extract_region_content(predicted, "line_item_table")
    if pred_table and isinstance(pred_table, list):
        gt_items = ground_truth.get('items', [])
        # Convert ground truth items to same format
        gt_table = [
            {
                "description": item.get('description', ''),
                "quantity": item.get('quantity', 0),
                "unit_price": item.get('unit_price', 0.0),
                "line_total": item.get('total', item.get('subtotal', 0.0) + item.get('tax_amount', 0.0) - item.get('discount', 0.0))
            }
            for item in gt_items
        ]
        
        teds_score, teds_metrics = table_structure_accuracy(pred_table, gt_table)
        results["table_accuracy"] = {
            "teds_score": teds_score,
            **teds_metrics
        }
    
    # Numerical validation
    is_valid, errors = numerical_validation(predicted)
    results["numerical_validation"] = {
        "is_valid": is_valid,
        "errors": errors
    }
    
    return results


def evaluate_dataset(
    predictions: List[str],
    ground_truths: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evaluate an entire dataset.
    
    Args:
        predictions: List of predicted JSON responses
        ground_truths: List of ground truth metadata dictionaries
        
    Returns:
        Aggregated evaluation metrics
    """
    if len(predictions) != len(ground_truths):
        raise ValueError(f"Predictions ({len(predictions)}) and ground truths ({len(ground_truths)}) must have same length")
    
    all_results = []
    region_accuracies = defaultdict(list)
    teds_scores = []
    numerical_valid_count = 0
    
    for pred, gt in zip(predictions, ground_truths):
        result = evaluate_sample(pred, gt)
        all_results.append(result)
        
        # Aggregate field extraction accuracies
        for region, metrics in result.get("field_extraction", {}).items():
            region_accuracies[region].append(metrics["overall_accuracy"])
        
        # Aggregate table accuracy
        if result.get("table_accuracy"):
            teds_scores.append(result["table_accuracy"].get("teds_score", 0.0))
        
        # Count numerical validation
        if result.get("numerical_validation", {}).get("is_valid", False):
            numerical_valid_count += 1
    
    # Compute aggregated metrics
    aggregated = {
        "region_accuracies": {
            region: {
                "mean": np.mean(scores),
                "std": np.std(scores),
                "min": np.min(scores),
                "max": np.max(scores)
            }
            for region, scores in region_accuracies.items()
        },
        "table_accuracy": {
            "mean_teds": np.mean(teds_scores) if teds_scores else 0.0,
            "std_teds": np.std(teds_scores) if teds_scores else 0.0
        },
        "numerical_validation": {
            "valid_count": numerical_valid_count,
            "total_count": len(predictions),
            "valid_rate": numerical_valid_count / len(predictions) if predictions else 0.0
        },
        "overall_sample_count": len(predictions)
    }
    
    return aggregated

