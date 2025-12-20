# Monetization System Setup Guide

This guide explains how to set up and configure the monetization system for FinScribe Smart Scan.

## Overview

The monetization system includes:
- ✅ SaaS subscription tiers (Free, Starter, Pro, Enterprise)
- ✅ API usage billing with credits
- ✅ Document usage metering and overages
- ✅ Stripe integration for payments
- ✅ Partner attribution (QuickBooks/Xero revenue share)
- ✅ Feature gating middleware
- ✅ Accounting system connectors
- ✅ Revenue dashboard APIs

## Database Setup

1. **Run the migration:**
   ```bash
   # If using Supabase
   supabase migration up
   
   # Or apply the SQL directly:
   psql -d your_database -f supabase/migrations/20251220200000_monetization_schema.sql
   ```

2. **Verify tables created:**
   - `profiles` (extended with billing fields)
   - `document_usage`
   - `billing_cycles`
   - `partners`
   - `partner_referrals`
   - `licenses`
   - `marketplace_models`
   - `premium_feature_purchases`

## Stripe Configuration

1. **Get your Stripe API keys:**
   - Sign up at https://stripe.com
   - Get your test API keys from the dashboard
   - For production, use live keys

2. **Set environment variables:**
   ```bash
   export STRIPE_SECRET_KEY=sk_test_...
   export STRIPE_PUBLISHABLE_KEY=pk_test_...
   ```

3. **Create Stripe Products & Prices:**
   - Create products for each plan (Starter, Pro)
   - Copy the Price IDs
   - Set environment variables:
     ```bash
     export STRIPE_PRICE_ID_STARTER=price_...
     export STRIPE_PRICE_ID_PRO=price_...
     ```

4. **Configure webhook endpoint:**
   - In Stripe Dashboard → Webhooks
   - Add endpoint: `https://your-domain.com/api/v1/billing/webhook`
   - Select events: `invoice.paid`, `customer.subscription.updated`, `customer.subscription.deleted`
   - Copy webhook signing secret:
     ```bash
     export STRIPE_WEBHOOK_SECRET=whsec_...
     ```

## Frontend Configuration

1. **Set API URL:**
   ```bash
   # In .env or .env.local
   VITE_API_URL=http://localhost:8000
   ```

2. **Update checkout URLs:**
   - Edit `src/lib/checkout.ts` if using custom domain
   - Update success/cancel URLs in `app/api/v1/billing.py`

## Integration Points

### 1. Document Usage Tracking

After a document is successfully processed, call:

```python
from app.billing.usage import record_document_usage

# In your document processing completion handler:
record_document_usage(
    db=db_session,
    user_id=user.id,
    document_id=document_id,
    pages=page_count,
    plan_tier=user.plan
)
```

**Location:** Add this in `app/core/worker.py` after successful processing (around line 88).

### 2. Feature Gating

Protect premium features in your endpoints:

```python
from app.middleware.feature_gate import enforce_feature

@router.post("/batch-process")
async def batch_process(request: Request):
    await enforce_feature(request, "batch_processing")
    # ... rest of endpoint
```

### 3. API Credits

For API endpoints that consume credits:

```python
from app.billing.credits import has_api_credits, deduct_api_credits

@router.post("/api/analyze")
async def api_analyze(request: Request):
    user = request.state.user
    if not has_api_credits(user, required=1):
        raise HTTPException(402, "Out of API credits")
    deduct_api_credits(db, user, amount=1)
    # ... process request
```

### 4. Accounting Integrations

After processing an invoice, push to accounting systems:

```python
from app.integrations.accounting import get_connector

if user.has_integration("quickbooks"):
    connector = get_connector("quickbooks", user.quickbooks_token)
    result = connector.push_invoice(parsed_invoice_data)
```

## Testing

### Test Stripe Checkout:
1. Use test card: `4242 4242 4242 4242`
2. Any future expiry date
3. Any 3-digit CVC

### Test Partner Attribution:
1. Sign up with: `https://your-app.com/signup?partner=quickbooks`
2. Complete checkout
3. Check `partner_referrals` table for revenue share record

## Environment Variables Summary

```bash
# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_PRICE_ID_STARTER=price_...
STRIPE_PRICE_ID_PRO=price_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Frontend
VITE_API_URL=http://localhost:8000

# Accounting (optional)
QUICKBOOKS_ACCESS_TOKEN=...
QUICKBOOKS_COMPANY_ID=...
XERO_ACCESS_TOKEN=...
XERO_TENANT_ID=...
```

## Revenue Dashboard

Access admin endpoints:
- `/api/v1/billing/admin/revenue` - Overall revenue summary
- `/api/v1/billing/admin/partners/revenue` - Partner revenue breakdown

**Note:** Add authentication/authorization middleware for production.

## Next Steps

1. ✅ Database migration applied
2. ✅ Stripe keys configured
3. ✅ Webhook endpoint set up
4. ⬜ Integrate usage tracking in document processor
5. ⬜ Add feature gates to premium endpoints
6. ⬜ Set up accounting integrations (if needed)
7. ⬜ Test end-to-end checkout flow
8. ⬜ Configure production Stripe account

## Support

For issues or questions:
- Check logs: `app/billing/` modules log to standard logger
- Stripe Dashboard: Monitor webhook events
- Database: Check `billing_cycles` and `document_usage` tables

