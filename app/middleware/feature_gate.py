"""
Feature Gating Middleware - Critical for monetization
"""
from fastapi import Request, HTTPException, status
from app.pricing.plans import PLANS, PlanTier, has_feature


async def enforce_feature(request: Request, feature: str):
    """
    Enforce feature access based on user's plan.
    Raises HTTPException if feature is not available.
    
    Usage in endpoints:
        await enforce_feature(request, "batch_processing")
    """
    # Get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    plan_tier = getattr(user, "plan", "free")
    
    if not has_feature(plan_tier, feature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Feature '{feature}' not available on {plan_tier} plan. Please upgrade."
        )


def check_feature_access(plan_tier: str, feature: str) -> bool:
    """
    Check if a plan tier has access to a feature.
    Returns True/False without raising exceptions.
    """
    return has_feature(plan_tier, feature)

