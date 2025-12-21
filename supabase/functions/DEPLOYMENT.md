# Edge Functions Deployment Guide

## Quick Start

### 1. Prerequisites

```bash
# Install Supabase CLI
npm install -g supabase

# Login to Supabase
supabase login

# Link your project
supabase link --project-ref your-project-ref
```

### 2. Set Environment Secrets

```bash
# Required secrets
supabase secrets set SUPABASE_URL=https://your-project.supabase.co
supabase secrets set SUPABASE_ANON_KEY=your-anon-key
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Stripe (for stripe-webhook function)
supabase secrets set STRIPE_SECRET_KEY=sk_live_...
supabase secrets set STRIPE_WEBHOOK_SECRET=whsec_...
supabase secrets set STRIPE_PUBLISHABLE_KEY=pk_live_...

# Optional
supabase secrets set FRONTEND_URL=https://your-app.com
supabase secrets set API_URL=https://api.your-app.com
supabase secrets set ENVIRONMENT=production
```

### 3. Deploy Functions

```bash
# Deploy all functions
supabase functions deploy

# Deploy specific function
supabase functions deploy stripe-webhook
supabase functions deploy document-upload
supabase functions deploy usage-tracking
supabase functions deploy image-processor
```

### 4. Configure Stripe Webhook

1. Go to Stripe Dashboard → Webhooks
2. Add endpoint: `https://your-project.supabase.co/functions/v1/stripe-webhook`
3. Select events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
   - `checkout.session.completed`
4. Copy the webhook signing secret
5. Set it as `STRIPE_WEBHOOK_SECRET` secret

### 5. Test Functions

```bash
# Test locally (requires Supabase local setup)
supabase functions serve

# Test deployed function
curl -X POST https://your-project.supabase.co/functions/v1/usage-tracking \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "test", "pages": 1}'
```

## Function URLs

After deployment, your functions will be available at:

- `https://your-project.supabase.co/functions/v1/stripe-webhook`
- `https://your-project.supabase.co/functions/v1/document-upload`
- `https://your-project.supabase.co/functions/v1/usage-tracking`
- `https://your-project.supabase.co/functions/v1/image-processor`

## Local Development

```bash
# Start Supabase locally
supabase start

# Serve functions locally
supabase functions serve

# Functions will be available at:
# http://localhost:54321/functions/v1/<function-name>
```

## Monitoring

- View logs: `supabase functions logs <function-name>`
- View in dashboard: Supabase Dashboard → Edge Functions → [Function Name] → Logs
- Set up alerts in Supabase dashboard for errors

## Troubleshooting

### Function not found
- Ensure function is deployed: `supabase functions list`
- Check function name matches exactly (case-sensitive)

### Authentication errors
- Verify `SUPABASE_ANON_KEY` is set correctly
- Check Authorization header format: `Bearer <token>`

### Database errors
- Ensure `SUPABASE_SERVICE_ROLE_KEY` is set for admin operations
- Check RLS policies allow the operation
- Verify table names match your schema

### Stripe webhook errors
- Verify webhook secret is correct
- Check webhook URL in Stripe dashboard
- Ensure event types are selected in Stripe


