# Supabase Integration

This directory contains the Supabase integration for FinScribe Smart Scan. It provides a complete, type-safe, and production-ready integration with Supabase Auth, Database, and Storage.

## 📁 Structure

```
src/integrations/supabase/
├── client.ts          # Supabase client initialization
├── types.ts           # Generated TypeScript types from database schema
├── utils.ts           # Utility functions for common operations
├── index.ts           # Centralized exports
└── README.md          # This file
```

## 🚀 Quick Start

### Basic Usage

```tsx
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import { useProfile } from '@/hooks/useSupabase';

// In a component
function MyComponent() {
  const { user, signIn, signOut } = useAuth();
  const { data: profile, isLoading } = useProfile();

  // Use auth methods
  const handleLogin = async () => {
    const { error } = await signIn('user@example.com', 'password');
    if (error) console.error(error);
  };

  return <div>{profile?.full_name}</div>;
}
```

## 🔐 Authentication

### Using the Auth Context

The `AuthProvider` wraps your app and provides authentication state and methods:

```tsx
import { AuthProvider } from '@/contexts/AuthContext';
import { useAuth } from '@/contexts/AuthContext';

// In App.tsx
<AuthProvider>
  <YourApp />
</AuthProvider>

// In components
const { user, session, signIn, signUp, signOut, signInWithOAuth } = useAuth();
```

### Available Auth Methods

- `signIn(email, password)` - Sign in with email/password
- `signUp(email, password, options?)` - Create a new account
- `signOut()` - Sign out the current user
- `signInWithOAuth(provider)` - Sign in with OAuth (google, github, twitter)
- `resetPassword(email)` - Send password reset email
- `updatePassword(newPassword)` - Update user password

### Protected Routes

Use the `ProtectedRoute` component to protect routes:

```tsx
import { ProtectedRoute } from '@/components/ProtectedRoute';

<Route
  path="/dashboard"
  element={
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  }
/>
```

## 📊 Data Fetching with React Query

### Profile Management

```tsx
import { useProfile, useUpdateProfile } from '@/hooks/useSupabase';

function ProfilePage() {
  const { data: profile, isLoading } = useProfile();
  const updateProfile = useUpdateProfile();

  const handleUpdate = async () => {
    await updateProfile.mutateAsync({
      full_name: 'John Doe',
      avatar_url: 'https://...',
    });
  };

  if (isLoading) return <div>Loading...</div>;
  return <div>{profile?.full_name}</div>;
}
```

### Custom Queries

```tsx
import { useSupabaseQuery } from '@/hooks/useSupabase';

const { data, isLoading, error } = useSupabaseQuery(
  'profiles',
  async (client) => {
    return await client.from('profiles').select('*').eq('id', userId);
  },
  { enabled: !!userId }
);
```

### Custom Mutations

```tsx
import { useSupabaseMutation } from '@/hooks/useSupabase';

const mutation = useSupabaseMutation(
  async (client, variables: { name: string }) => {
    return await client
      .from('profiles')
      .insert({ name: variables.name })
      .select()
      .single();
  },
  { invalidateQueries: [['profiles']] }
);

// Use it
mutation.mutate({ name: 'John' });
```

## 💾 Storage Operations

```tsx
import { uploadFile, getPublicUrl, deleteFile } from '@/integrations/supabase/utils';

// Upload a file
const { path } = await uploadFile('documents', 'user-123/invoice.pdf', file, {
  contentType: 'application/pdf',
  upsert: true,
});

// Get public URL
const url = getPublicUrl('documents', 'user-123/invoice.pdf');

// Delete files
await deleteFile('documents', ['user-123/invoice.pdf']);
```

## 🔔 Realtime Subscriptions

```tsx
import { subscribeToTable } from '@/integrations/supabase/utils';
import { useEffect } from 'react';

useEffect(() => {
  const unsubscribe = subscribeToTable<Profile>(
    'profiles',
    `id=eq.${userId}`,
    (payload) => {
      console.log('Profile updated:', payload);
    }
  );

  return unsubscribe;
}, [userId]);
```

## 📄 Pagination

```tsx
import { paginateQuery } from '@/integrations/supabase/utils';

const result = await paginateQuery(
  supabase.from('profiles'),
  {
    page: 1,
    pageSize: 20,
    orderBy: 'created_at',
    order: 'desc',
  }
);

// result: { data, page, pageSize, total, hasMore }
```

## 🛠️ Utility Functions

### Error Handling

```tsx
import { handleSupabaseError, isSupabaseError } from '@/integrations/supabase/utils';

try {
  await someSupabaseOperation();
} catch (error) {
  if (isSupabaseError(error)) {
    const message = handleSupabaseError(error);
    toast.error(message);
  }
}
```

### Batch Operations

```tsx
import { batchInsert, batchUpdate, batchDelete } from '@/integrations/supabase/utils';

// Batch insert
await batchInsert('profiles', [
  { email: 'user1@example.com' },
  { email: 'user2@example.com' },
]);

// Batch update
await batchUpdate('profiles', { status: 'active' }, 'id', userId);

// Batch delete
await batchDelete('profiles', 'status', 'inactive');
```

## 🔒 Security Best Practices

1. **Never expose service role key** - Only use it in Edge Functions
2. **Use Row Level Security (RLS)** - Enable RLS policies in Supabase
3. **Validate inputs** - Always validate user inputs before database operations
4. **Handle errors gracefully** - Use `handleSupabaseError` for user-friendly messages
5. **Use protected routes** - Wrap sensitive routes with `ProtectedRoute`

## 📝 Type Safety

All database operations are fully typed based on your database schema:

```tsx
import type { Profile, ProfileInsert, ProfileUpdate } from '@/hooks/useSupabase';

const profile: Profile = {
  id: '...',
  email: 'user@example.com',
  // TypeScript will enforce correct types
};
```

## 🧪 Testing

When testing components that use Supabase:

1. Mock the Supabase client in tests
2. Use React Query's testing utilities for hooks
3. Test error cases with `handleSupabaseError`

```tsx
// Example test setup
jest.mock('@/integrations/supabase/client', () => ({
  supabase: {
    auth: { ... },
    from: jest.fn(),
  },
}));
```

## 🐛 Troubleshooting

### "Missing env.VITE_SUPABASE_URL"

Make sure your `.env` file contains:
```
VITE_SUPABASE_URL=your-project-url
VITE_SUPABASE_PUBLISHABLE_KEY=your-anon-key
```

### Authentication not persisting

Check that `localStorage` is available (not in SSR context) and that the client is configured with `persistSession: true`.

### Type errors

Run `supabase gen types typescript` to regenerate types after schema changes.

## 📚 Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Auth Helpers](https://supabase.com/docs/guides/auth)
- [React Query Documentation](https://tanstack.com/query/latest)

