/**
 * Configuration utilities for Supabase Edge Functions
 */

/**
 * Get environment variable with fallback
 */
export function getEnv(key: string, defaultValue?: string): string {
  const value = Deno.env.get(key);
  if (!value && defaultValue === undefined) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value || defaultValue || "";
}

/**
 * Get Supabase configuration
 */
export function getSupabaseConfig() {
  return {
    url: getEnv("SUPABASE_URL"),
    anonKey: getEnv("SUPABASE_ANON_KEY"),
    serviceRoleKey: getEnv("SUPABASE_SERVICE_ROLE_KEY", ""),
  };
}

/**
 * Get Stripe configuration
 */
export function getStripeConfig() {
  return {
    secretKey: getEnv("STRIPE_SECRET_KEY", ""),
    webhookSecret: getEnv("STRIPE_WEBHOOK_SECRET", ""),
    publishableKey: getEnv("STRIPE_PUBLISHABLE_KEY", ""),
  };
}

/**
 * Get application configuration
 */
export function getAppConfig() {
  return {
    frontendUrl: getEnv("FRONTEND_URL", "http://localhost:5173"),
    apiUrl: getEnv("API_URL", "http://localhost:8000"),
    environment: getEnv("ENVIRONMENT", "development"),
  };
}

