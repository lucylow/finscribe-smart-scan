"""
Pricing & Plan Definitions - Single Source of Truth
"""
from enum import Enum
from typing import Dict, List, Optional


class PlanTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


PLANS: Dict[PlanTier, Dict] = {
    PlanTier.FREE: {
        "price_usd": 0,
        "monthly_docs": 50,
        "api_access": False,
        "features": ["basic_fields"],
        "overage_price": None,
        "stripe_price_id": None,  # Set in environment
    },
    PlanTier.STARTER: {
        "price_usd": 49,
        "monthly_docs": 500,
        "api_access": True,
        "features": ["full_json", "csv_export"],
        "overage_price": 0.25,
        "stripe_price_id": None,  # Set in environment
    },
    PlanTier.PRO: {
        "price_usd": 149,
        "monthly_docs": 5000,
        "api_access": True,
        "features": [
            "batch_processing",
            "accounting_integrations",
            "webhooks",
        ],
        "overage_price": 0.15,
        "stripe_price_id": None,  # Set in environment
    },
    PlanTier.ENTERPRISE: {
        "price_usd": None,
        "monthly_docs": None,
        "api_access": True,
        "features": ["custom_fields", "on_prem", "sla"],
        "overage_price": 0.10,
        "stripe_price_id": None,  # Set in environment
    },
}


def get_plan(tier: str) -> Optional[Dict]:
    """Get plan configuration by tier name."""
    try:
        plan_enum = PlanTier(tier.lower())
        return PLANS[plan_enum]
    except ValueError:
        return None


def has_feature(plan_tier: str, feature: str) -> bool:
    """Check if a plan tier includes a specific feature."""
    plan = get_plan(plan_tier)
    if not plan:
        return False
    return feature in plan.get("features", [])


def get_monthly_quota(plan_tier: str) -> Optional[int]:
    """Get monthly document quota for a plan."""
    plan = get_plan(plan_tier)
    if not plan:
        return None
    return plan.get("monthly_docs")


