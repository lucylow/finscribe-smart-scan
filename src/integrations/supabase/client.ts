import { createClient, SupabaseClient } from '@supabase/supabase-js';
import type { Database } from './types';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_PUBLISHABLE_KEY = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

// Create a mock client if env vars are missing (for development/Lovable)
const createMockClient = (): SupabaseClient<Database> => {
  console.warn(
    '⚠️ Supabase environment variables not set. Using mock client. ' +
    'Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY to enable authentication.'
  );
  
  // Return a client with dummy values that will fail gracefully
  return createClient<Database>(
    SUPABASE_URL || 'https://placeholder.supabase.co',
    SUPABASE_PUBLISHABLE_KEY || 'placeholder-key',
    {
      auth: {
        storage: typeof window !== 'undefined' ? localStorage : undefined,
        persistSession: false,
        autoRefreshToken: false,
        detectSessionInUrl: false,
        flowType: 'pkce',
      },
      global: {
        headers: {
          'X-Client-Info': 'finscribe-smart-scan',
        },
      },
    }
  );
};

/**
 * Supabase client instance
 * 
 * Import and use like this:
 * ```ts
 * import { supabase } from "@/integrations/supabase/client";
 * ```
 * 
 * Note: If environment variables are not set, a mock client will be created
 * that will fail gracefully when used. Set VITE_SUPABASE_URL and 
 * VITE_SUPABASE_PUBLISHABLE_KEY in your environment to enable authentication.
 */
export const supabase: SupabaseClient<Database> = 
  SUPABASE_URL && SUPABASE_PUBLISHABLE_KEY
    ? createClient<Database>(
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
      )
    : createMockClient();

/**
 * Helper to check if Supabase is properly configured
 */
export function isSupabaseConfigured(): boolean {
  return !!SUPABASE_URL && !!SUPABASE_PUBLISHABLE_KEY && 
         SUPABASE_URL !== 'https://placeholder.supabase.co' &&
         SUPABASE_PUBLISHABLE_KEY !== 'placeholder-key';
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
