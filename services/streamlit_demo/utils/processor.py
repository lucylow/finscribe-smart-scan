"""
Processing utilities for calculating metrics and improvements.
"""
from typing import Dict, Any, List


def calculate_improvement_metrics(
    ft_results: Dict[str, Any],
    vanilla_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate improvement metrics comparing fine-tuned vs vanilla results.
    
    Args:
        ft_results: Fine-tuned model results
        vanilla_results: Vanilla model results
        
    Returns:
        Dictionary with improvement metrics
    """
    metrics = {
        'confidence_improvement': 0.0,
        'field_extraction_improvement': 0,
        'validation_improvement': 0.0,
        'error_reduction': 0,
        'overall_score': 0.0
    }
    
    # Confidence improvement
    ft_conf = ft_results.get('validation', {}).get('overall_confidence', 0.0)
    vanilla_conf = vanilla_results.get('validation', {}).get('overall_confidence', 0.0)
    if vanilla_conf > 0:
        metrics['confidence_improvement'] = ((ft_conf - vanilla_conf) / vanilla_conf) * 100
    else:
        metrics['confidence_improvement'] = ft_conf * 100 if ft_conf > 0 else 0.0
    
    # Field extraction improvement
    ft_fields = len(ft_results.get('data', {}).get('line_items', []))
    vanilla_fields = len(vanilla_results.get('data', {}).get('line_items', []))
    metrics['field_extraction_improvement'] = ft_fields - vanilla_fields
    
    # Validation improvement (boolean to percentage)
    ft_valid = 1.0 if ft_results.get('validation', {}).get('is_valid', False) else 0.0
    vanilla_valid = 1.0 if vanilla_results.get('validation', {}).get('is_valid', False) else 0.0
    metrics['validation_improvement'] = (ft_valid - vanilla_valid) * 100
    
    # Error reduction
    ft_errors = len(ft_results.get('validation', {}).get('errors', []))
    vanilla_errors = len(vanilla_results.get('validation', {}).get('errors', []))
    metrics['error_reduction'] = vanilla_errors - ft_errors
    
    # Overall score (weighted average)
    metrics['overall_score'] = (
        metrics['confidence_improvement'] * 0.3 +
        metrics['field_extraction_improvement'] * 10 * 0.2 +  # Scale up field count
        metrics['validation_improvement'] * 0.3 +
        metrics['error_reduction'] * 10 * 0.2  # Scale up error reduction
    )
    
    return metrics


def extract_key_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key fields from structured data for comparison.
    
    Args:
        data: Structured data dictionary
        
    Returns:
        Dictionary with key fields
    """
    return {
        'vendor_name': data.get('vendor', {}).get('name'),
        'invoice_number': data.get('client', {}).get('invoice_number'),
        'invoice_date': data.get('client', {}).get('dates', {}).get('invoice_date'),
        'grand_total': data.get('financial_summary', {}).get('grand_total'),
        'subtotal': data.get('financial_summary', {}).get('subtotal'),
        'line_items_count': len(data.get('line_items', []))
    }


def format_currency(value: Any, currency: str = 'USD') -> str:
    """
    Format a numeric value as currency.
    
    Args:
        value: Numeric value to format
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    if value is None:
        return 'N/A'
    
    try:
        num_value = float(value)
        if currency == 'USD':
            return f"${num_value:,.2f}"
        else:
            return f"{currency} {num_value:,.2f}"
    except (ValueError, TypeError):
        return str(value) if value else 'N/A'


def calculate_processing_speedup(ft_time: float, vanilla_time: float) -> Dict[str, Any]:
    """
    Calculate processing speed improvements.
    
    Args:
        ft_time: Fine-tuned processing time (seconds)
        vanilla_time: Vanilla processing time (seconds)
        
    Returns:
        Dictionary with speed metrics
    """
    if vanilla_time == 0:
        return {
            'speedup_ratio': 1.0,
            'speedup_percentage': 0.0,
            'time_saved': 0.0
        }
    
    speedup_ratio = vanilla_time / ft_time if ft_time > 0 else 1.0
    speedup_percentage = ((vanilla_time - ft_time) / vanilla_time) * 100
    time_saved = vanilla_time - ft_time
    
    return {
        'speedup_ratio': speedup_ratio,
        'speedup_percentage': speedup_percentage,
        'time_saved': time_saved,
        'ft_time': ft_time,
        'vanilla_time': vanilla_time
    }
