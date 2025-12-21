import { createClient, SupabaseClient } from '@supabase/supabase-js';
import type { Database } from './types';

// NOTE: Lovable projects should NOT rely on VITE_* env vars at runtime.
// This app is connected to Supabase project: dvypmevjyxdeyhaofued
const SUPABASE_URL = "https://dvypmevjyxdeyhaofued.supabase.co";

// Supabase anon key is safe to expose in the browser (it is not the service role key).
const SUPABASE_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR2eXBtZXZqeXhkZXloYW9mdWVkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYyNTc4MzIsImV4cCI6MjA4MTgzMzgzMn0.cSVG9NlwCl6czffzmzx7PVyFz1fkM-yx2aXuZIy_kac";


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
  SUPABASE_ANON_KEY,
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
  return !!SUPABASE_URL && !!SUPABASE_ANON_KEY;
}

/**
 * Get Supabase configuration (for debugging/logging)
 */
export function getSupabaseConfig() {
  return {
    url: SUPABASE_URL,
    hasKey: !!SUPABASE_ANON_KEY,
    keyLength: SUPABASE_ANON_KEY?.length || 0,
  };
}
