# FinScribe AI - SaaS Implementation Guide

This document outlines the comprehensive SaaS implementation for FinScribe AI, including multi-tenant architecture, subscription management, usage tracking, and billing systems.

## 📁 Implementation Overview

### Core Components

1. **Multi-Tenant Database Models** (`app/db/saas_models.py`)
   - `Tenant` - Customer organizations
   - `TenantUser` - Users within tenants
   - `Subscription` - Subscription history
   - `Invoice` - Billing invoices
   - `APIKey` - API authentication keys
   - `TenantIntegration` - Third-party integrations
   - `UsageRecord` - Usage tracking records

2. **Subscription Manager** (`app/pricing/subscription_manager.py`)
   - Comprehensive pricing tiers (Starter, Growth, Professional, Enterprise)
   - Feature flags and limits
   - Addon management
   - Promotion codes
   - Usage-based overage calculations

3. **Usage Tracker** (`app/pricing/usage_tracker.py`)
   - Real-time usage tracking with Redis
   - Quota management
   - Usage alerts
   - Analytics and reporting

4. **API Gateway** (`app/api/middleware/api_gateway.py`)
   - API key authentication
   - Rate limiting per tenant
   - Usage tracking
   - Performance monitoring

5. **Revenue Calculator** (`app/pricing/revenue_calculator.py`)
   - Financial projections
   - LTV/CAC calculations
   - Break-even analysis
   - Investor deck metrics

6. **SaaS Dashboard** (`src/components/finscribe/SaaSDashboard.tsx`)
   - Real-time metrics
   - Usage visualization
   - Subscription management
   - Activity tracking

## 🚀 Setup Instructions

### 1. Database Migration

Run the Alembic migration to create SaaS tables:

```bash
alembic upgrade head
```

Or manually create tables:

```python
from app.db import init_db
init_db()  # Creates all tables including SaaS models
```

### 2. Redis Setup (Optional but Recommended)

For production usage tracking and rate limiting:

```bash
# Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
brew install redis  # macOS
# or
apt-get install redis-server  # Linux
```

Set environment variables:

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
```

The system will gracefully fall back to in-memory storage if Redis is unavailable.

### 3. Stripe Integration

Configure Stripe for billing:

```bash
export STRIPE_SECRET_KEY=sk_test_...
export STRIPE_PUBLISHABLE_KEY=pk_test_...
```

### 4. Environment Variables

Add to your `.env` file:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/finscribe

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

# Supabase (for user auth)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-key
```

## 📊 Usage Examples

### Creating a Tenant

```python
from app.db import SessionLocal
from app.db.saas_models import Tenant
from datetime import datetime

db = SessionLocal()

tenant = Tenant(
    name="Acme Corp",
    domain="acme.finscribe.ai",
    industry="technology",
    subscription_tier="growth",
    payment_plan="monthly",
    limits={
        "monthly_document_limit": 5000,
        "user_limit": 10,
        "api_rate_limit": 10000,
        "storage_limit_gb": 50
    }
)

db.add(tenant)
db.commit()
```

### Tracking Usage

```python
from app.pricing.usage_tracker import UsageTracker, UsageEvent
from datetime import datetime

tracker = UsageTracker()

event = UsageEvent(
    tenant_id="tenant_123",
    user_id="user_456",
    event_type="document_processed",
    resource="documents",
    quantity=1.0,
    metadata={"document_id": "doc_789", "pages": 3}
)

tracker.track_usage(event)
```

### Calculating Subscription Price

```python
from app.pricing.subscription_manager import SaaSSubscriptionManager

manager = SaaSSubscriptionManager()

# Calculate price with addons and promotion
price = manager.calculate_subscription_price(
    tier_code="growth",
    billing_cycle="annual",
    addons=["advanced_integrations"],
    promo_code="LAUNCH20"
)

print(f"Total: ${price['total']:.2f}/month")
print(f"Features: {price['features']}")
```

### Checking Feature Access

```python
from app.pricing.subscription_manager import SaaSSubscriptionManager, Feature

manager = SaaSSubscriptionManager()

# Check if tenant has access to feature
has_access = manager.check_feature_access("growth", Feature.API_ACCESS)
print(f"Has API access: {has_access}")
```

### Financial Projections

```python
from app.pricing.revenue_calculator import FinancialProjections

calculator = FinancialProjections()

# Get investor deck numbers
projections = calculator.generate_investor_deck_numbers(
    model_name="subscription",
    years=5
)

print(f"Year 5 MRR: ${projections['year_5_projections']['ending_mrr']:,.2f}")
print(f"LTV: ${projections['ltv_analysis']['ltv']:,.2f}")
print(f"LTV:CAC Ratio: {projections['ltv_analysis']['ltv_cac_ratio']:.2f}")
```

## 🔌 API Integration

### Adding API Gateway Middleware

In your FastAPI app (`app/main.py`):

```python
from fastapi import FastAPI
from app.api.middleware.api_gateway import api_gateway_middleware

app = FastAPI()

# Add middleware
app.middleware("http")(api_gateway_middleware)

# Your routes...
@app.get("/api/v1/documents")
async def list_documents(request: Request):
    tenant_id = request.state.tenant_id  # Set by middleware
    # Your logic here
```

### API Key Authentication

Clients can authenticate using API keys:

```bash
curl -H "X-API-Key: sk_live_..." https://api.finscribe.ai/v1/documents
```

Rate limits are automatically enforced based on subscription tier.

## 📈 Dashboard Integration

To use the SaaS dashboard in your React app:

```tsx
import SaaSDashboard from "@/components/finscribe/SaaSDashboard";

// In your route/page
<SaaSDashboard />
```

The dashboard component expects an API endpoint at `/api/v1/dashboard` that returns:

```json
{
  "overview": {
    "documentsProcessed": 1247,
    "mrr": 199,
    "activeUsers": 8,
    "accuracy": 98.5,
    "documentsRemaining": 3753,
    "quota": 5000
  },
  "usage": [...],
  "subscription": {...},
  "recentActivity": [...]
}
```

## 💰 Pricing Tiers

### Starter - $49/month
- 500 documents/month
- 3 users
- 10 GB storage
- 1,000 API requests/month
- Basic OCR features

### Growth - $199/month
- 5,000 documents/month
- 10 users
- 50 GB storage
- 10,000 API requests/month
- Advanced OCR, multi-currency, integrations

### Professional - $499/month
- 25,000 documents/month
- 25 users
- 100 GB storage
- 50,000 API requests/month
- All features + workflow automation, webhooks

### Enterprise - $999+/month
- 100,000+ documents/month
- 100+ users
- 500+ GB storage
- 200,000+ API requests/month
- All features + custom models, white-label, SLA

## 🔐 Security Considerations

1. **API Keys**: Store hashed, never plain text
2. **Credentials**: Encrypt integration credentials at rest
3. **Rate Limiting**: Enforce per-tenant limits
4. **Row-Level Security**: Implement tenant isolation in database queries
5. **Audit Logging**: Track all sensitive operations

## 📝 Next Steps

1. **Implement API Endpoints**: Create REST APIs for tenant management, billing, etc.
2. **Stripe Webhooks**: Handle subscription events (payment, cancellation, etc.)
3. **Email Notifications**: Send usage alerts, invoice notifications
4. **Admin Panel**: Build admin interface for managing tenants
5. **Testing**: Add comprehensive unit and integration tests
6. **Documentation**: Create API documentation with OpenAPI/Swagger

## 🐛 Troubleshooting

### Redis Connection Issues

If Redis is unavailable, the system automatically falls back to in-memory storage. Check logs:

```python
import logging
logging.getLogger("app.pricing.usage_tracker").setLevel(logging.DEBUG)
```

### Database Migration Errors

If migration fails, check database connection and ensure all dependencies are installed:

```bash
pip install -r requirements.txt
alembic current
alembic upgrade head
```

### Rate Limiting Not Working

Ensure Redis is running and middleware is properly configured:

```python
# Check Redis connection
import redis
r = redis.Redis(host='localhost', port=6379)
r.ping()  # Should return True
```

## 📚 Additional Resources

- [Stripe API Documentation](https://stripe.com/docs/api)
- [Redis Documentation](https://redis.io/docs/)
- [SQLAlchemy Multi-Tenancy](https://docs.sqlalchemy.org/en/14/orm/examples.html)
- [FastAPI Middleware](https://fastapi.tiangolo.com/tutorial/middleware/)

## 🤝 Contributing

When adding new features:

1. Update database models in `app/db/saas_models.py`
2. Create Alembic migration
3. Update subscription manager if adding new features/limits
4. Add tests in `tests/`
5. Update this documentation

---

**Note**: This is a comprehensive SaaS implementation. For production use, ensure proper security hardening, error handling, and monitoring are in place.

