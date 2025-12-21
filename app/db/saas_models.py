"""
Multi-tenant SaaS database models for FinScribe AI
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
from typing import Dict, Optional

from . import Base


class SubscriptionTier(str, enum.Enum):
    """Subscription tier enumeration"""
    STARTER = "starter"
    GROWTH = "growth"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class PaymentPlan(str, enum.Enum):
    """Payment plan enumeration"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    USAGE_BASED = "usage_based"
    REVENUE_SHARE = "revenue_share"


class InvoiceStatus(str, enum.Enum):
    """Invoice status enumeration"""
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    VOID = "void"


class Tenant(Base):
    """SaaS tenant (customer organization)"""
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    domain = Column(String, unique=True, nullable=True)
    industry = Column(String, nullable=True)  # construction, healthcare, legal, etc.
    country = Column(String, default="US")
    timezone = Column(String, default="UTC")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Subscription
    subscription_tier = Column(String, default=SubscriptionTier.STARTER.value)
    payment_plan = Column(String, default=PaymentPlan.MONTHLY.value)
    subscription_start = Column(DateTime, default=datetime.utcnow)
    subscription_end = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    auto_renew = Column(Boolean, default=True)
    
    # Limits (stored as JSON for flexibility)
    limits = Column(JSON, default={
        "monthly_document_limit": 500,
        "user_limit": 3,
        "api_rate_limit": 1000,  # requests per hour
        "storage_limit_gb": 10
    })
    
    # Billing
    monthly_recurring_revenue = Column(Float, default=0.0)
    total_revenue = Column(Float, default=0.0)
    last_invoice_date = Column(DateTime, nullable=True)
    next_billing_date = Column(DateTime, nullable=True)
    
    # Stripe integration
    stripe_customer_id = Column(String, nullable=True, unique=True)
    stripe_subscription_id = Column(String, nullable=True, unique=True)
    
    # Metadata
    metadata = Column(JSON, default={})
    
    # Relationships
    users = relationship("TenantUser", back_populates="tenant", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="tenant", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="tenant", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="tenant", cascade="all, delete-orphan")
    integrations = relationship("TenantIntegration", back_populates="tenant", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="tenant", cascade="all, delete-orphan")
    
    def get_usage_stats(self) -> Dict:
        """Get current usage statistics (to be implemented with actual queries)"""
        from datetime import datetime
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # This would query actual usage records
        docs_this_month = sum(
            1 for record in self.usage_records 
            if record.created_at >= month_start and record.resource_type == "document"
        )
        
        return {
            "documents_processed_this_month": docs_this_month,
            "documents_remaining": max(0, self.limits.get("monthly_document_limit", 0) - docs_this_month),
            "users_active": len([u for u in self.users if u.is_active]),
            "storage_used_gb": self._get_storage_used(),
            "api_requests_this_month": self._get_api_request_count(),
            "next_billing_date": self.next_billing_date.isoformat() if self.next_billing_date else None,
            "subscription_value": self.monthly_recurring_revenue
        }
    
    def can_process_document(self) -> bool:
        """Check if tenant can process another document"""
        if self.subscription_tier == SubscriptionTier.ENTERPRISE.value:
            return True
        
        limit = self.limits.get("monthly_document_limit", 0)
        if limit is None:  # Unlimited
            return True
        
        stats = self.get_usage_stats()
        return stats["documents_processed_this_month"] < limit
    
    def _get_storage_used(self) -> float:
        """Get storage used in GB (placeholder - implement with actual calculation)"""
        # Would calculate from document sizes
        return 0.0
    
    def _get_api_request_count(self) -> int:
        """Get API request count for current month (placeholder)"""
        from datetime import datetime
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return sum(
            1 for record in self.usage_records 
            if record.created_at >= month_start and record.resource_type == "api_request"
        )


class TenantUser(Base):
    """User within a tenant organization"""
    __tablename__ = "tenant_users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # User info
    email = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="user")  # admin, manager, user, viewer
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Supabase auth integration (optional)
    supabase_user_id = Column(String, nullable=True, unique=True)
    
    # Preferences
    preferences = Column(JSON, default={})
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        role_permissions = {
            "admin": ["read", "write", "delete", "manage_users", "manage_billing"],
            "manager": ["read", "write", "manage_users"],
            "user": ["read", "write"],
            "viewer": ["read"]
        }
        return permission in role_permissions.get(self.role, [])


class Subscription(Base):
    """Subscription history and changes"""
    __tablename__ = "subscriptions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Subscription details
    tier = Column(String, nullable=False)
    plan = Column(String, nullable=False)
    monthly_price = Column(Float, nullable=False)
    
    # Period
    start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    
    # Changes
    previous_subscription_id = Column(String, ForeignKey("subscriptions.id"), nullable=True)
    change_reason = Column(String, nullable=True)  # upgrade, downgrade, cancellation
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="subscriptions")
    previous_subscription = relationship("Subscription", remote_side=[id])


class Invoice(Base):
    """Billing invoices"""
    __tablename__ = "invoices"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Invoice details
    invoice_number = Column(String, unique=True, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=False)
    
    # Amounts
    subtotal = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    
    # Line items
    line_items = Column(JSON, default=[])  # List of charge items
    
    # Payment
    status = Column(String, default=InvoiceStatus.PENDING.value)
    paid_at = Column(DateTime, nullable=True)
    payment_method = Column(String, nullable=True)
    stripe_invoice_id = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="invoices")


class APIKey(Base):
    """API keys for programmatic access"""
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("tenant_users.id", ondelete="SET NULL"), nullable=True)
    
    # Key details
    key = Column(String, unique=True, nullable=False)
    key_prefix = Column(String, nullable=False)  # First 8 chars for display
    name = Column(String, nullable=True)
    permissions = Column(JSON, default=[])  # List of allowed endpoints/actions
    rate_limit = Column(Integer, default=100)  # requests per minute
    
    # Expiry
    expires_at = Column(DateTime, nullable=True)
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="api_keys")
    user = relationship("TenantUser", back_populates="api_keys")
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new API key"""
        import secrets
        return f"sk_live_{secrets.token_urlsafe(32)}"


class TenantIntegration(Base):
    """Third-party integrations for tenants"""
    __tablename__ = "tenant_integrations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Integration details
    integration_type = Column(String, nullable=False)  # accounting, payment, etc.
    service_name = Column(String, nullable=False)  # quickbooks, xero, stripe
    connection_status = Column(String, default="disconnected")  # connected, disconnected, error
    
    # Credentials (encrypted in production)
    api_key = Column(Text, nullable=True)
    api_secret = Column(Text, nullable=True)
    additional_config = Column(JSON, default={})
    
    # Sync settings
    auto_sync = Column(Boolean, default=False)
    last_sync_at = Column(DateTime, nullable=True)
    sync_frequency = Column(String, default="daily")  # hourly, daily, weekly
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="integrations")


class UsageRecord(Base):
    """Usage tracking records for billing and analytics"""
    __tablename__ = "usage_records"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("tenant_users.id", ondelete="SET NULL"), nullable=True)
    
    # Usage details
    resource_type = Column(String, nullable=False)  # document, api_request, storage_gb
    quantity = Column(Float, nullable=False, default=1.0)
    unit = Column(String, nullable=True)  # document, request, gb
    
    # Metadata
    metadata = Column(JSON, default={})  # Additional context
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="usage_records")


