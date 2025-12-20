"""
Document Usage Metering - Per-Document Billing
"""
import logging
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.pricing.plans import PLANS, PlanTier, get_plan

logger = logging.getLogger(__name__)


def get_current_billing_cycle(db: Session, user_id: str) -> dict:
    """
    Get or create the current billing cycle for a user.
    Returns a dict with cycle info (in production, this would be a DB model).
    """
    today = date.today()
    period_start = date(today.year, today.month, 1)
    
    # Calculate period end (last day of current month)
    if today.month == 12:
        period_end = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        period_end = date(today.year, today.month + 1, 1) - timedelta(days=1)
    
    # In production, query billing_cycles table
    # For now, return a dict structure
    return {
        "user_id": user_id,
        "period_start": period_start,
        "period_end": period_end,
        "docs_used": 0,  # Would be fetched from DB
        "overage_cost_usd": 0.0,
    }


def record_document_usage(
    db: Session,
    user_id: str,
    document_id: str,
    pages: int = 1,
    plan_tier: str = "free"
) -> dict:
    """
    Record document usage and calculate overages.
    Call this after OCR completes successfully.
    
    Returns dict with usage info and any overage charges.
    """
    try:
        cycle = get_current_billing_cycle(db, user_id)
        cycle["docs_used"] += 1
        
        plan = get_plan(plan_tier)
        if not plan:
            logger.warning(f"Unknown plan tier: {plan_tier}, defaulting to free")
            plan = get_plan("free")
        
        quota = plan.get("monthly_docs")
        overage_price = plan.get("overage_price")
        
        overage_cost = 0.0
        if quota and cycle["docs_used"] > quota and overage_price:
            overage_docs = cycle["docs_used"] - quota
            overage_cost = overage_docs * overage_price
            cycle["overage_cost_usd"] += overage_cost
        
        # In production, save to database:
        # db.execute(
        #     "INSERT INTO document_usage (user_id, document_id, pages) VALUES (:user_id, :doc_id, :pages)",
        #     {"user_id": user_id, "doc_id": document_id, "pages": pages}
        # )
        # db.execute(
        #     "UPDATE billing_cycles SET docs_used = :docs, overage_cost_usd = :cost WHERE user_id = :user_id AND period_start = :start",
        #     {"docs": cycle["docs_used"], "cost": cycle["overage_cost_usd"], "user_id": user_id, "start": cycle["period_start"]}
        # )
        # db.commit()
        
        return {
            "docs_used": cycle["docs_used"],
            "quota": quota,
            "overage_cost": overage_cost,
            "within_quota": quota is None or cycle["docs_used"] <= quota,
        }
    except Exception as e:
        logger.error(f"Error recording document usage: {str(e)}", exc_info=True)
        raise


def check_quota(db: Session, user_id: str, plan_tier: str) -> dict:
    """
    Check if user has remaining quota.
    Returns dict with quota info.
    """
    cycle = get_current_billing_cycle(db, user_id)
    plan = get_plan(plan_tier)
    
    if not plan:
        return {"has_quota": False, "remaining": 0, "quota": 0}
    
    quota = plan.get("monthly_docs")
    if quota is None:  # Unlimited (enterprise)
        return {"has_quota": True, "remaining": None, "quota": None}
    
    remaining = max(0, quota - cycle["docs_used"])
    return {
        "has_quota": remaining > 0,
        "remaining": remaining,
        "quota": quota,
        "used": cycle["docs_used"],
    }

