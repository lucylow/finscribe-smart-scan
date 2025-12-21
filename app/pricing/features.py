"""
Premium AI Features Pricing
"""
from typing import Dict, Optional

PREMIUM_FEATURE_COSTS: Dict[str, float] = {
    "vendor_risk_scoring": 149,
    "cashflow_forecast": 199,
    "benchmark_reports": 99,
}


def feature_price(feature: str) -> Optional[float]:
    """Get the price for a premium feature."""
    return PREMIUM_FEATURE_COSTS.get(feature)


def is_premium_feature(feature: str) -> bool:
    """Check if a feature is premium (requires payment)."""
    return feature in PREMIUM_FEATURE_COSTS


