/**
 * Error handling utilities for Supabase Edge Functions
 */

import type { FunctionResponse } from "./types.ts";
import { corsResponse } from "./cors.ts";

export class FunctionError extends Error {
  constructor(
    message: string,
    public statusCode: number = 500,
    public code?: string
  ) {
    super(message);
    this.name = "FunctionError";
  }
}

/**
 * Handle errors and return appropriate response
 */
export function handleError(
  error: unknown,
  request: Request
): Response {
  console.error("Function error:", error);

  if (error instanceof FunctionError) {
    const response: FunctionResponse = {
      success: false,
      error: error.code || "FUNCTION_ERROR",
      message: error.message,
    };
    return corsResponse(response, error.statusCode, request.headers.get("origin"));
  }

  if (error instanceof Error) {
    const response: FunctionResponse = {
      success: false,
      error: "INTERNAL_ERROR",
      message: error.message,
    };
    return corsResponse(response, 500, request.headers.get("origin"));
  }

  const response: FunctionResponse = {
    success: false,
    error: "UNKNOWN_ERROR",
    message: "An unknown error occurred",
  };
  return corsResponse(response, 500, request.headers.get("origin"));
}

/**
 * Create success response
 */
export function successResponse<T>(
  data: T,
  message?: string,
  request?: Request
): Response {
  const response: FunctionResponse<T> = {
    success: true,
    data,
    message,
  };
  return corsResponse(response, 200, request?.headers.get("origin") || null);
}

