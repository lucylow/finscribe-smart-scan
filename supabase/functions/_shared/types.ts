/**
 * Shared TypeScript types for Supabase Edge Functions
 */

export interface CorsHeaders {
  "Access-Control-Allow-Origin": string;
  "Access-Control-Allow-Headers": string;
  "Access-Control-Allow-Methods": string;
  "Content-Type"?: string;
  [key: string]: string | undefined;
}

export interface FunctionResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface SupabaseClient {
  from: (table: string) => {
    select: (columns?: string) => Promise<{ data: unknown; error: unknown }>;
    insert: (data: unknown) => Promise<{ data: unknown; error: unknown }>;
    update: (data: unknown) => Promise<{ data: unknown; error: unknown }>;
    delete: () => Promise<{ data: unknown; error: unknown }>;
    eq: (column: string, value: unknown) => unknown;
  };
  auth: {
    getUser: (token: string) => Promise<{ data: { user: unknown }; error: unknown }>;
  };
}

export interface StripeWebhookEvent {
  id: string;
  type: string;
  data: {
    object: {
      id: string;
      customer?: string;
      subscription?: string;
      status?: string;
      metadata?: Record<string, string>;
      [key: string]: unknown;
    };
  };
}


