/**
 * Usage Tracking Edge Function
 * 
 * Tracks document usage, checks quotas, and records usage events.
 * Helps enforce subscription limits and calculate overages.
 */

// Deno.serve is the standard way to serve Supabase Edge Functions
import { createClient, SupabaseClient } from "https://esm.sh/@supabase/supabase-js@2";
import { handleCors } from "../_shared/cors.ts";
import { handleError, successResponse, FunctionError } from "../_shared/errors.ts";
import { requireAuth } from "../_shared/auth.ts";
import { getSupabaseConfig } from "../_shared/config.ts";

interface UsageEvent {
  document_id?: string;
  pages?: number;
  event_type?: string;
  metadata?: Record<string, unknown>;
}

interface UsageResponse {
  usage: {
    docs_used: number;
    quota: number | null;
    remaining: number | null;
    has_quota: boolean;
  };
  recorded: boolean;
}

// Get current usage for user in current billing cycle
async function getCurrentUsage(
  userId: string,
  supabaseClient: SupabaseClient
): Promise<{ docsUsed: number; quota: number | null; plan: string }> {
  // Get user plan
  const { data: profile, error: profileError } = await supabaseClient
    .from("profiles")
    .select("*")
    .eq("id", userId)
    .single();

  if (profileError) {
    console.error("Error fetching profile:", profileError);
    throw new FunctionError("Failed to fetch user profile", 500, "DATABASE_ERROR");
  }

  const plan = ((profile as Record<string, unknown>)?.plan as string) || "free";

  // Define quotas by plan (you should sync this with your pricing plans)
  const quotas: Record<string, number | null> = {
    free: 10,
    starter: 100,
    pro: 1000,
    enterprise: null, // unlimited
  };

  const quota = quotas[plan] ?? null;

  // Get current billing cycle start (beginning of month)
  const now = new Date();
  const cycleStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();

  // Get usage for current cycle
  const { data: usage, error: usageError } = await supabaseClient
    .from("document_usage")
    .select("pages")
    .eq("user_id", userId)
    .gte("processed_at", cycleStart);

  if (usageError) {
    console.error("Error fetching usage:", usageError);
    // If table doesn't exist, return 0 usage
    return { docsUsed: 0, quota, plan };
  }

  const docsUsed = usage?.length || 0;

  return { docsUsed, quota, plan };
}

// Record usage event
async function recordUsage(
  userId: string,
  event: UsageEvent,
  supabaseClient: SupabaseClient
): Promise<void> {
  const usageData = {
    user_id: userId,
    document_id: event.document_id || null,
    pages: event.pages || 1,
    processed_at: new Date().toISOString(),
  };

  const { error } = await supabaseClient
    .from("document_usage")
    .insert(usageData as Record<string, unknown>);

  if (error) {
    console.error("Error recording usage:", error);
    throw new FunctionError(
      `Failed to record usage: ${error.message}`,
      500,
      "DATABASE_ERROR"
    );
  }
}

// Update billing cycle
async function updateBillingCycle(
  userId: string,
  docsUsed: number,
  supabaseClient: SupabaseClient
): Promise<void> {
  const now = new Date();
  const periodStart = new Date(now.getFullYear(), now.getMonth(), 1)
    .toISOString()
    .split("T")[0];
  const periodEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0)
    .toISOString()
    .split("T")[0];

  const { error } = await supabaseClient
    .from("billing_cycles")
    .upsert({
      user_id: userId,
      period_start: periodStart,
      period_end: periodEnd,
      docs_used: docsUsed,
      updated_at: new Date().toISOString(),
    } as Record<string, unknown>, {
      onConflict: "user_id,period_start",
    });

  if (error) {
    console.error("Error updating billing cycle:", error);
    // Don't throw - this is non-critical
  }
}

Deno.serve(async (request) => {
  // Handle CORS preflight
  const corsPreflightResponse = handleCors(request);
  if (corsPreflightResponse) return corsPreflightResponse;

  try {
    const config = getSupabaseConfig();
    const supabaseClient = createClient(config.url, config.anonKey, {
      global: { headers: { Authorization: request.headers.get("Authorization") || "" } },
    });

    // Authenticate user
    const user = await requireAuth(request, config.url, config.anonKey);

    if (request.method === "POST") {
      // Record usage
      const event: UsageEvent = await request.json();

      // Get current usage
      const { docsUsed, quota } = await getCurrentUsage(user.id, supabaseClient);

      // Check quota if applicable
      if (quota !== null && docsUsed >= quota) {
        throw new FunctionError(
          `Usage quota exceeded. ${docsUsed}/${quota} documents used this month.`,
          403,
          "QUOTA_EXCEEDED"
        );
      }

      // Record the usage
      await recordUsage(user.id, event, supabaseClient);

      // Update billing cycle
      await updateBillingCycle(user.id, docsUsed + 1, supabaseClient);

      // Get updated usage
      const { docsUsed: newDocsUsed, quota: newQuota } = await getCurrentUsage(
        user.id,
        supabaseClient
      );

      const response: UsageResponse = {
        usage: {
          docs_used: newDocsUsed,
          quota: newQuota,
          remaining: newQuota !== null ? Math.max(0, newQuota - newDocsUsed) : null,
          has_quota: newQuota !== null,
        },
        recorded: true,
      };

      return successResponse(response, "Usage recorded successfully", request);
    } else if (request.method === "GET") {
      // Get current usage
      const { docsUsed, quota } = await getCurrentUsage(user.id, supabaseClient);

      const response: UsageResponse = {
        usage: {
          docs_used: docsUsed,
          quota: quota,
          remaining: quota !== null ? Math.max(0, quota - docsUsed) : null,
          has_quota: quota !== null,
        },
        recorded: false,
      };

      return successResponse(response, "Usage retrieved successfully", request);
    }

    throw new FunctionError("Method not allowed", 405, "METHOD_NOT_ALLOWED");
  } catch (error) {
    return handleError(error, request);
  }
});
