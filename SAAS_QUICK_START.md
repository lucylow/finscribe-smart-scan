# FinScribe SaaS - Quick Start Guide

This guide will help you quickly get started with the SaaS implementation for FinScribe AI.

## 🎯 What's Included

✅ **Multi-tenant architecture** with complete database models  
✅ **Subscription management** with 4 pricing tiers  
✅ **Usage tracking** with Redis support  
✅ **API gateway** with rate limiting  
✅ **Revenue calculator** for financial projections  
✅ **SaaS dashboard** React component  
✅ **Billing integration** with Stripe  

## 🚀 Quick Setup (5 minutes)

### 1. Install Dependencies

```bash
pip install redis stripe  # Add to requirements.txt if not already there
```

### 2. Run Database Migration

```bash
# Create the SaaS tables
alembic upgrade head
```

### 3. Start Redis (Optional but Recommended)

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
brew install redis  # macOS
sudo service redis-server start  # Linux
```

### 4. Set Environment Variables

```bash
# .env file
DATABASE_URL=postgresql://user:pass@localhost/finscribe
REDIS_HOST=localhost
REDIS_PORT=6379
STRIPE_SECRET_KEY=sk_test_...
```

## 📝 Basic Usage

### Create a Tenant

```python
from app.db import SessionLocal
from app.db.saas_models import Tenant

db = SessionLocal()

tenant = Tenant(
    name="My Company",
    subscription_tier="growth",
    payment_plan="monthly",
    limits={
        "monthly_document_limit": 5000,
        "user_limit": 10,
        "api_rate_limit": 10000
    }
)
db.add(tenant)
db.commit()
```

### Track Usage

```python
from app.pricing.usage_tracker import UsageTracker, UsageEvent

tracker = UsageTracker()

tracker.track_usage(UsageEvent(
    tenant_id="tenant_123",
    event_type="document_processed",
    resource="documents",
    quantity=1.0,
    metadata={}
))
```

### Check Quota

```python
limits = {"documents": 5000}
quota_check = tracker.check_quota("tenant_123", "documents", 1, limits)

if not quota_check["has_quota"]:
    print(f"Quota exceeded! Used {quota_check['current_usage']}/{quota_check['limit']}")
```

### Calculate Subscription Price

```python
from app.pricing.subscription_manager import SaaSSubscriptionManager

manager = SaaSSubscriptionManager()

price = manager.calculate_subscription_price(
    tier_code="growth",
    billing_cycle="annual",
    promo_code="LAUNCH20"
)

print(f"Total: ${price['total']:.2f}/month")
```

### Use Dashboard Component

```tsx
// In your React component
import SaaSDashboard from "@/components/finscribe/SaaSDashboard";

<SaaSDashboard />
```

## 🔌 API Integration

### Add to FastAPI Router

```python
from app.api.v1.dashboard import router as dashboard_router

app.include_router(dashboard_router, prefix="/api/v1")
```

### Add API Gateway Middleware

```python
from app.api.middleware.api_gateway import api_gateway_middleware

app.middleware("http")(api_gateway_middleware)
```

### Authenticate with API Key

```bash
curl -H "X-API-Key: sk_live_..." https://api.finscribe.ai/api/v1/dashboard
```

## 💰 Pricing Tiers

| Tier | Price | Documents | Users | Storage | Features |
|------|-------|-----------|-------|---------|----------|
| Starter | $49/mo | 500 | 3 | 10 GB | Basic OCR, API |
| Growth | $199/mo | 5,000 | 10 | 50 GB | + Multi-currency, Integrations |
| Professional | $499/mo | 25,000 | 25 | 100 GB | + Workflows, Webhooks |
| Enterprise | $999+/mo | 100,000+ | 100+ | 500+ GB | + Custom models, White-label |

## 📊 Financial Projections

```python
from app.pricing.revenue_calculator import FinancialProjections

calculator = FinancialProjections()
projections = calculator.generate_investor_deck_numbers(years=5)

print(f"Year 5 MRR: ${projections['year_5_projections']['ending_mrr']:,.2f}")
print(f"LTV: ${projections['ltv_analysis']['ltv']:,.2f}")
```

## 🔍 Key Features

### 1. Multi-Tenancy
- Complete tenant isolation
- Per-tenant limits and quotas
- Tenant-specific configurations

### 2. Subscription Management
- Multiple pricing tiers
- Feature flags per tier
- Overage billing
- Promotion codes

### 3. Usage Tracking
- Real-time tracking with Redis
- Quota management
- Usage alerts
- Analytics and reporting

### 4. API Gateway
- API key authentication
- Rate limiting per tenant
- Usage tracking
- Performance monitoring

### 5. Billing
- Stripe integration
- Invoice generation
- Subscription management
- Payment tracking

## 📚 Next Steps

1. **Integrate with existing code**: Connect SaaS models to your document processing pipeline
2. **Set up Stripe**: Create products and prices in Stripe dashboard
3. **Add API endpoints**: Create REST APIs for tenant management
4. **Build admin panel**: Create interface for managing tenants
5. **Add tests**: Write tests for critical paths
6. **Deploy**: Set up production environment with Redis and Postgres

## 🆘 Troubleshooting

**Redis connection fails?**  
→ System automatically falls back to in-memory storage. Check logs for warnings.

**Migration errors?**  
→ Ensure database connection is working: `python -c "from app.db import engine; engine.connect()"`

**Rate limiting not working?**  
→ Check Redis is running: `redis-cli ping` should return `PONG`

## 📖 Full Documentation

See `SAAS_IMPLEMENTATION.md` for complete documentation.

---

**Need help?** Check the implementation guide or review the code in:
- `app/db/saas_models.py` - Database models
- `app/pricing/subscription_manager.py` - Pricing logic
- `app/pricing/usage_tracker.py` - Usage tracking
- `app/api/middleware/api_gateway.py` - API gateway
- `src/components/finscribe/SaaSDashboard.tsx` - Dashboard UI

