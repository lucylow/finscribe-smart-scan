"""
Pay-What-You-Save (ROI-Based Billing)
"""
from typing import Dict


def calculate_roi_fee(manual_cost_per_doc: float, docs_processed: int, fee_percentage: float = 0.03) -> float:
    """
    Calculate ROI-based fee based on savings.
    
    Args:
        manual_cost_per_doc: Cost of manual processing per document (in USD)
        docs_processed: Number of documents processed
        fee_percentage: Percentage of savings to charge (default 3%)
    
    Returns:
        Fee amount in USD (rounded to 2 decimal places)
    """
    savings = manual_cost_per_doc * docs_processed
    fee = savings * fee_percentage
    return round(fee, 2)


def calculate_manual_cost(
    avg_time_per_doc_minutes: float,
    hourly_rate_usd: float
) -> float:
    """
    Calculate manual processing cost per document.
    
    Args:
        avg_time_per_doc_minutes: Average time to process one document manually (minutes)
        hourly_rate_usd: Hourly rate for manual processing (USD)
    
    Returns:
        Cost per document in USD
    """
    hours_per_doc = avg_time_per_doc_minutes / 60.0
    return hours_per_doc * hourly_rate_usd


# Example usage:
# manual_cost = calculate_manual_cost(avg_time_per_doc_minutes=15, hourly_rate_usd=25)
# roi_fee = calculate_roi_fee(manual_cost, docs_processed=100)
# Store result in billing_cycles.overage_cost_usd

