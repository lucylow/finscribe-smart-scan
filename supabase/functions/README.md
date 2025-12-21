# Supabase Edge Functions

This directory contains Supabase Edge Functions for the FinScribe Smart Scan application.

## Functions

### 1. `stripe-webhook`
Handles Stripe webhook events for subscription management, payments, and billing updates.

**Features:**
- Webhook signature verification
- Subscription lifecycle management
- User profile updates
- Payment processing

**Usage:**
```bash
# Deploy
supabase functions deploy stripe-webhook

# Set secrets
supabase secrets set STRIPE_SECRET_KEY=sk_...
supabase secrets set STRIPE_WEBHOOK_SECRET=whsec_...
```

### 2. `document-upload`
Handles document uploads with validation and storage management.

**Features:**
- File validation (size, type)
- Secure storage in Supabase Storage
- Metadata recording
- Public URL generation

**Usage:**
```typescript
const formData = new FormData();
formData.append('file', file);
formData.append('metadata', JSON.stringify({ tags: ['invoice'] }));

const response = await fetch(
  'https://your-project.supabase.co/functions/v1/document-upload',
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  }
);
```

### 3. `usage-tracking`
Tracks document usage and enforces subscription quotas.

**Features:**
- Real-time usage tracking
- Quota enforcement
- Billing cycle management
- Usage history

**Usage:**
```typescript
// Record usage
await fetch(
  'https://your-project.supabase.co/functions/v1/usage-tracking',
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      document_id: 'doc-123',
      pages: 3,
      event_type: 'document_processed'
    })
  }
);

// Get usage
const response = await fetch(
  'https://your-project.supabase.co/functions/v1/usage-tracking',
  {
    headers: { 'Authorization': `Bearer ${token}` }
  }
);
```

### 4. `image-processor`
Processes and resizes images for previews and thumbnails.

**Features:**
- Image resizing
- Format conversion
- Quality adjustment
- Optimized storage

**Usage:**
```typescript
const response = await fetch(
  'https://your-project.supabase.co/functions/v1/image-processor',
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      filePath: 'user-id/filename.jpg',
      width: 800,
      height: 600,
      quality: 0.8,
      format: 'jpeg'
    })
  }
);
```

## Shared Utilities

The `_shared` directory contains reusable utilities:

- **`auth.ts`**: Authentication helpers
- **`cors.ts`**: CORS handling utilities
- **`errors.ts`**: Error handling and responses
- **`config.ts`**: Configuration management
- **`types.ts`**: TypeScript type definitions

## Development

### Local Development

1. Install Supabase CLI:
```bash
npm install -g supabase
```

2. Start local development:
```bash
supabase functions serve
```

3. Test locally:
```bash
curl -X POST http://localhost:54321/functions/v1/usage-tracking \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "test", "pages": 1}'
```

### Deployment

1. Deploy all functions:
```bash
supabase functions deploy
```

2. Deploy specific function:
```bash
supabase functions deploy stripe-webhook
```

3. Set secrets:
```bash
supabase secrets set STRIPE_SECRET_KEY=sk_...
supabase secrets set STRIPE_WEBHOOK_SECRET=whsec_...
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

## Environment Variables

Required secrets for edge functions:

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Supabase anonymous key
- `SUPABASE_SERVICE_ROLE_KEY`: Service role key (for admin operations)
- `STRIPE_SECRET_KEY`: Stripe API secret key
- `STRIPE_WEBHOOK_SECRET`: Stripe webhook signing secret
- `STRIPE_PUBLISHABLE_KEY`: Stripe publishable key
- `FRONTEND_URL`: Frontend application URL
- `API_URL`: Backend API URL
- `ENVIRONMENT`: Environment (development/production)

## Best Practices

1. **Error Handling**: All functions use standardized error handling via `_shared/errors.ts`
2. **Authentication**: All functions authenticate users via `requireAuth()` or `getAuthenticatedUser()`
3. **CORS**: All functions handle CORS properly via `_shared/cors.ts`
4. **Logging**: Use `console.log` and `console.error` for debugging (visible in Supabase dashboard)
5. **Security**: Always validate inputs and verify webhook signatures
6. **Type Safety**: Use TypeScript types from `_shared/types.ts`

## Testing

Test functions using the Supabase dashboard or via curl:

```bash
# Test with authentication
curl -X POST https://your-project.supabase.co/functions/v1/usage-tracking \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_id": "test-doc", "pages": 1}'
```

## Monitoring

Monitor function execution and logs in the Supabase dashboard:
- Navigate to Edge Functions
- View logs and metrics for each function
- Set up alerts for errors

## Improvements Made

1. ✅ **Type Safety**: Full TypeScript support with shared types
2. ✅ **Error Handling**: Standardized error responses
3. ✅ **Authentication**: Reusable auth utilities
4. ✅ **CORS**: Proper CORS handling for all functions
5. ✅ **Configuration**: Centralized config management
6. ✅ **Code Reusability**: Shared utilities across functions
7. ✅ **Security**: Webhook signature verification
8. ✅ **Validation**: Input validation and error messages
9. ✅ **Documentation**: Comprehensive README and code comments
10. ✅ **Best Practices**: Following Deno and Supabase best practices


