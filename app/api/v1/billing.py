"""
Billing API Endpoints - Stripe, Checkout, Usage, Revenue
"""
import os
import logging
from fastapi import APIRouter, HTTPException, Request, Header, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.billing.stripe import (
    create_checkout_session,
    create_customer,
    handle_webhook,
)
from app.billing.partners import record_partner_referral, record_revenue_share
from app.billing.usage import check_quota, record_document_usage
from app.billing.credits import has_api_credits, deduct_api_credits, add_api_credits
from app.pricing.plans import PLANS, PlanTier, get_plan

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models
class CheckoutRequest(BaseModel):
    plan: str
    partner_code: Optional[str] = None


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class UsageResponse(BaseModel):
    docs_used: int
    quota: Optional[int]
    remaining: Optional[int]
    has_quota: bool
    overage_cost: float


class RevenueSummary(BaseModel):
    monthly_recurring: float
    usage_overages: float
    enterprise_contracts: float
    partner_revenue: float


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: Request,
    checkout_data: CheckoutRequest
):
    """
    Create Stripe Checkout session for plan upgrade.
    """
    try:
        # Get user from request (set by auth middleware)
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Validate plan
        plan = get_plan(checkout_data.plan)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plan: {checkout_data.plan}"
            )
        
        # Get Stripe price ID from environment or plan config
        price_id = plan.get("stripe_price_id") or os.getenv(
            f"STRIPE_PRICE_ID_{checkout_data.plan.upper()}", ""
        )
        
        if not price_id:
            logger.warning(f"No Stripe price ID configured for plan: {checkout_data.plan}")
            # In production, this should be configured
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Payment configuration error. Please contact support."
            )
        
        # Get or create Stripe customer
        customer_id = getattr(user, "stripe_customer_id", None)
        if not customer_id:
            # Create Stripe customer
            customer = create_customer(
                email=getattr(user, "email", ""),
                metadata={"user_id": str(getattr(user, "id", ""))}
            )
            customer_id = customer["id"]
            # In production, save customer_id to user record
        
        # Build success/cancel URLs
        base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        success_url = f"{base_url}/app/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{base_url}/pricing"
        
        # Create checkout session
        metadata = {"plan": checkout_data.plan, "user_id": str(getattr(user, "id", ""))}
        if checkout_data.partner_code:
            metadata["partner_code"] = checkout_data.partner_code
        
        session = create_checkout_session(
            customer_id=customer_id,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata
        )
        
        return CheckoutResponse(
            checkout_url=session["url"],
            session_id=session["id"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating checkout: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None)
):
    """
    Handle Stripe webhook events.
    In production, verify webhook signature.
    """
    try:
        import json
        body = await request.body()
        event = json.loads(body)
        
        # In production, verify webhook signature:
        # stripe.Webhook.construct_event(body, stripe_signature, webhook_secret)
        
        result = handle_webhook(event)
        
        # Handle revenue share if invoice was paid
        if result.get("status") == "success" and result.get("event") == "invoice.paid":
            # In production, get user from database using customer_id
            # user = db.query(User).filter_by(stripe_customer_id=result["customer_id"]).first()
            # if user:
            #     record_revenue_share(
            #         db=db,
            #         user_id=user.id,
            #         invoice_id=result["invoice_id"],
            #         revenue_usd=result["amount"]
            #     )
            pass
        
        return result
    
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


@router.get("/usage", response_model=UsageResponse)
async def get_usage(request: Request):
    """Get current usage and quota for authenticated user."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    plan_tier = getattr(user, "plan", "free")
    user_id = str(getattr(user, "id", ""))
    
    # In production, use actual database session
    # For now, return mock data structure
    quota_info = check_quota(None, user_id, plan_tier)
    
    return UsageResponse(
        docs_used=quota_info.get("used", 0),
        quota=quota_info.get("quota"),
        remaining=quota_info.get("remaining"),
        has_quota=quota_info.get("has_quota", False),
        overage_cost=0.0,  # Would be calculated from billing_cycles
    )


@router.get("/credits")
async def get_credits(request: Request):
    """Get API credits for authenticated user."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    credits = getattr(user, "api_credits", 0)
    return {"credits": credits, "has_credits": credits > 0}


@router.post("/credits/deduct")
async def deduct_credits(
    request: Request,
    amount: int = 1
):
    """Deduct API credits (used internally by API endpoints)."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # In production, use database session
    try:
        deduct_api_credits(None, user, amount)
        return {"success": True, "credits_remaining": getattr(user, "api_credits", 0)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deducting credits: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deduct credits"
        )


@router.get("/admin/revenue", response_model=RevenueSummary)
async def revenue_summary(request: Request):
    """
    Admin endpoint for revenue dashboard.
    In production, add admin authentication check.
    """
    # Mock data - in production, query database
    return RevenueSummary(
        monthly_recurring=0.0,  # Calculate from active subscriptions
        usage_overages=0.0,  # Sum from billing_cycles.overage_cost_usd
        enterprise_contracts=0.0,  # Sum from enterprise licenses
        partner_revenue=0.0,  # Sum from partner_referrals.revenue_usd
    )


@router.get("/admin/partners/revenue")
async def partner_revenue(request: Request):
    """
    Admin endpoint for partner revenue breakdown.
    """
    # Mock data - in production:
    # SELECT p.name, SUM(r.revenue_usd) as total
    # FROM partner_referrals r
    # JOIN partners p ON p.id = r.partner_id
    # GROUP BY p.name
    return {
        "partners": [
            {"name": "QuickBooks", "total_revenue": 0.0},
            {"name": "Xero", "total_revenue": 0.0},
        ]
    }


