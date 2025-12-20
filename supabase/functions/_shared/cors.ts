/**
 * CORS utilities for Supabase Edge Functions
 */

import type { CorsHeaders } from "./types.ts";

const DEFAULT_ALLOWED_ORIGINS = "*";
const DEFAULT_ALLOWED_HEADERS = "authorization, x-client-info, apikey, content-type";
const DEFAULT_ALLOWED_METHODS = "GET, POST, PUT, DELETE, OPTIONS";

/**
 * Get CORS headers with configurable options
 */
export function getCorsHeaders(
  origin: string | null = DEFAULT_ALLOWED_ORIGINS,
  allowedHeaders: string = DEFAULT_ALLOWED_HEADERS,
  allowedMethods: string = DEFAULT_ALLOWED_METHODS
): CorsHeaders {
  return {
    "Access-Control-Allow-Origin": origin || DEFAULT_ALLOWED_ORIGINS,
    "Access-Control-Allow-Headers": allowedHeaders,
    "Access-Control-Allow-Methods": allowedMethods,
  };
}

/**
 * Handle OPTIONS request for CORS preflight
 */
export function handleCors(request: Request): Response | null {
  if (request.method === "OPTIONS") {
    const headers = getCorsHeaders(
      request.headers.get("origin"),
      request.headers.get("access-control-request-headers") || undefined,
      request.headers.get("access-control-request-method") || undefined
    );
    return new Response(null, { status: 204, headers });
  }
  return null;
}

/**
 * Create a CORS-enabled response
 */
export function corsResponse(
  data: unknown,
  status: number = 200,
  origin: string | null = null
): Response {
  const headers = getCorsHeaders(origin);
  headers["Content-Type"] = "application/json";
  
  return new Response(
    JSON.stringify(data),
    { status, headers }
  );
}

