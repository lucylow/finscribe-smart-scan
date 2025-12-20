/**
 * Authentication utilities for Supabase Edge Functions
 */

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { FunctionError } from "./errors.ts";

export interface AuthenticatedUser {
  id: string;
  email?: string;
  [key: string]: unknown;
}

/**
 * Get authenticated user from request
 */
export async function getAuthenticatedUser(
  request: Request,
  supabaseUrl: string,
  supabaseAnonKey: string
): Promise<AuthenticatedUser | null> {
  try {
    const authHeader = request.headers.get("Authorization");
    if (!authHeader) {
      return null;
    }

    const token = authHeader.replace("Bearer ", "");
    if (!token) {
      return null;
    }

    const supabase = createClient(supabaseUrl, supabaseAnonKey, {
      global: { headers: { Authorization: authHeader } },
    });

    const { data: { user }, error } = await supabase.auth.getUser(token);
    
    if (error || !user) {
      console.error("Auth error:", error);
      return null;
    }

    return user as AuthenticatedUser;
  } catch (error) {
    console.error("Error authenticating user:", error);
    return null;
  }
}

/**
 * Require authentication - throws if user is not authenticated
 */
export async function requireAuth(
  request: Request,
  supabaseUrl: string,
  supabaseAnonKey: string
): Promise<AuthenticatedUser> {
  const user = await getAuthenticatedUser(request, supabaseUrl, supabaseAnonKey);
  if (!user) {
    throw new FunctionError("Unauthorized", 401, "UNAUTHORIZED");
  }
  return user;
}

