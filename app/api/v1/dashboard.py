"""
SaaS Dashboard API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime, timedelta

from app.db import get_db
from app.db.saas_models import Tenant, TenantUser
from app.pricing.usage_tracker import UsageTracker
from app.pricing.subscription_manager import SaaSSubscriptionManager

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=Dict[str, Any])
async def get_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get dashboard overview data for the current tenant.
    Requires authentication (API key or user session).
    """
    # Get tenant ID from request state (set by middleware)
    tenant_id = getattr(request.state, "tenant_id", None)
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get usage stats
    tracker = UsageTracker()
    usage_stats = tenant.get_usage_stats()
    
    # Get current month usage details
    current_month = datetime.now().strftime("%Y-%m")
    usage_data = tracker.get_tenant_usage(tenant_id, current_month)
    
    # Get subscription manager
    manager = SaaSSubscriptionManager()
    tier = manager.get_tier(tenant.subscription_tier)
    
    # Calculate documents remaining
    documents_used = int(usage_data.get("documents", 0))
    documents_limit = tenant.limits.get("monthly_document_limit", 0) if tenant.limits else 0
    documents_remaining = max(0, documents_limit - documents_used) if documents_limit else None
    
    # Get recent activity (placeholder - would query from activity log)
    recent_activity = []
    
    # Get active users count
    active_users = db.query(TenantUser).filter(
        TenantUser.tenant_id == tenant_id,
        TenantUser.is_active == True
    ).count()
    
    # Build response
    return {
        "overview": {
            "documentsProcessed": documents_used,
            "mrr": tenant.monthly_recurring_revenue,
            "activeUsers": active_users,
            "accuracy": 98.5,  # Would calculate from actual results
            "documentsRemaining": documents_remaining,
            "quota": documents_limit,
        },
        "usage": [
            {
                "month": (datetime.now() - timedelta(days=90 - i*30)).strftime("%b"),
                "documents": int(usage_data.get("documents", 0) * (0.8 + i*0.05)),
                "apiCalls": int(usage_data.get("api_requests", 0) * (0.8 + i*0.05)),
            }
            for i in range(4)
        ],
        "subscription": {
            "tier": tier.name if tier else tenant.subscription_tier,
            "tierCode": tenant.subscription_tier,
            "billingCycle": tenant.payment_plan,
            "nextBillingDate": tenant.next_billing_date.isoformat() if tenant.next_billing_date else None,
            "monthlyPrice": tenant.monthly_recurring_revenue,
            "status": "active" if tenant.is_active else "inactive",
        },
        "recentActivity": recent_activity,
        "usageAlerts": _check_usage_alerts(tracker, tenant) if tier else [],
    }


def _check_usage_alerts(tracker: UsageTracker, tenant: Tenant) -> list:
    """Check for usage alerts"""
    alerts = []
    
    if tenant.limits:
        for resource, limit in tenant.limits.items():
            if resource.endswith("_limit") and limit:
                resource_type = resource.replace("_limit", "").replace("monthly_document", "documents")
                alert = tracker.create_usage_alert(
                    tenant.id,
                    resource_type,
                    threshold_percent=80,
                    limits={resource_type: limit}
                )
                if alert:
                    alerts.append({
                        "type": "warning",
                        "title": f"{resource_type.replace('_', ' ').title()} Usage",
                        "message": f"You've used {alert['usage_percent']:.0f}% of your monthly {resource_type} quota",
                    })
    
    return alerts


@router.get("/usage", response_model=Dict[str, Any])
async def get_usage_stats(
    request: Request,
    db: Session = Depends(get_db),
    month: str = None
):
    """Get detailed usage statistics"""
    tenant_id = getattr(request.state, "tenant_id", None)
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    tracker = UsageTracker()
    usage = tracker.get_tenant_usage(tenant_id, month)
    
    return {
        "tenant_id": tenant_id,
        "month": month,
        "usage": usage,
        "currency": "USD"
    }


@router.get("/subscription", response_model=Dict[str, Any])
async def get_subscription_details(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get subscription details"""
    tenant_id = getattr(request.state, "tenant_id", None)
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    manager = SaaSSubscriptionManager()
    tier = manager.get_tier(tenant.subscription_tier)
    
    return {
        "tier": tier.name if tier else tenant.subscription_tier,
        "tierCode": tenant.subscription_tier,
        "billingCycle": tenant.payment_plan,
        "nextBillingDate": tenant.next_billing_date.isoformat() if tenant.next_billing_date else None,
        "monthlyPrice": tenant.monthly_recurring_revenue,
        "status": "active" if tenant.is_active else "inactive",
        "features": [f.value for f in tier.features] if tier else [],
        "limits": tenant.limits or {},
        "autoRenew": tenant.auto_renew,
    }

