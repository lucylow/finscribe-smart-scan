import { createClient, SupabaseClient } from '@supabase/supabase-js';
import type { Database } from './types';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_PUBLISHABLE_KEY = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

// Validate environment variables
if (!SUPABASE_URL) {
  throw new Error(
    'Missing env.VITE_SUPABASE_URL, see https://supabase.com/docs/guides/getting-started/quickstart#environment-variables'
  );
}

if (!SUPABASE_PUBLISHABLE_KEY) {
  throw new Error(
    'Missing env.VITE_SUPABASE_PUBLISHABLE_KEY, see https://supabase.com/docs/guides/getting-started/quickstart#environment-variables'
  );
}

/**
 * Supabase client instance
 * 
 * Import and use like this:
 * ```ts
 * import { supabase } from "@/integrations/supabase/client";
 * ```
 */
export const supabase: SupabaseClient<Database> = createClient<Database>(
  SUPABASE_URL,
  SUPABASE_PUBLISHABLE_KEY,
  {
    auth: {
      storage: typeof window !== 'undefined' ? localStorage : undefined,
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
      flowType: 'pkce',
    },
    global: {
      headers: {
        'X-Client-Info': 'finscribe-smart-scan',
      },
    },
  }
);

/**
 * Helper to check if Supabase is properly configured
 */
export function isSupabaseConfigured(): boolean {
  return !!SUPABASE_URL && !!SUPABASE_PUBLISHABLE_KEY;
}

/**
 * Get Supabase configuration (for debugging/logging)
 */
export function getSupabaseConfig() {
  return {
    url: SUPABASE_URL,
    hasKey: !!SUPABASE_PUBLISHABLE_KEY,
    keyLength: SUPABASE_PUBLISHABLE_KEY?.length || 0,
  };
}
