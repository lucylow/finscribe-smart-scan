/**
 * Stripe Webhook Handler Edge Function
 * 
 * Handles Stripe webhook events for subscription updates, payments, etc.
 * Verifies webhook signature and processes events securely.
 */

// Note: In production, you should use the official Stripe webhook verification
// This is a simplified implementation for demonstration

// Deno.serve is the standard way to serve Supabase Edge Functions
import { createClient, SupabaseClient } from "https://esm.sh/@supabase/supabase-js@2";
import { handleCors, corsResponse } from "../_shared/cors.ts";
import { handleError, successResponse } from "../_shared/errors.ts";
import { getSupabaseConfig, getStripeConfig } from "../_shared/config.ts";
import type { StripeWebhookEvent } from "../_shared/types.ts";

// Verify Stripe webhook signature
async function verifyStripeSignature(
  payload: string,
  signature: string | null,
  secret: string
): Promise<boolean> {
  if (!signature || !secret) {
    console.warn("Missing signature or secret for webhook verification");
    return false; // In production, you should return false and fail
  }

  try {
    // Import crypto for signature verification
    const encoder = new TextEncoder();
    const timestamp = signature.split(",").find((part) => part.startsWith("t="))?.split("=")[1];
    const signatures = signature.split(",").filter((part) => part.startsWith("v1=")).map((part) => part.split("=")[1]);

    if (!timestamp || signatures.length === 0) {
      return false;
    }

    const signedPayload = `${timestamp}.${payload}`;
    const secretKey = await crypto.subtle.importKey(
      "raw",
      encoder.encode(secret),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"]
    );

    const signatureBytes = await crypto.subtle.sign(
      "HMAC",
      secretKey,
      encoder.encode(signedPayload)
    );

    const expectedSignature = Array.from(new Uint8Array(signatureBytes))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");

    // Compare signatures (timing-safe comparison would be better)
    return signatures.some((sig) => sig === expectedSignature);
  } catch (error) {
    console.error("Error verifying signature:", error);
    return false;
  }
}

// Process Stripe webhook events
async function processWebhookEvent(
  event: StripeWebhookEvent,
  supabaseClient: SupabaseClient
) {
  const { type, data } = event;
  const object = data.object;

  console.log(`Processing Stripe webhook event: ${type}`);

  switch (type) {
    case "customer.subscription.created":
    case "customer.subscription.updated": {
      const customerId = object.customer as string;
      const subscriptionId = object.id;
      const status = object.status as string;
      const metadata = (object.metadata as Record<string, string>) || {};
      const plan = metadata.plan || "free";

      // Update user profile with subscription info
      const { error } = await supabaseClient
        .from("profiles")
        .update({
          plan: plan,
          updated_at: new Date().toISOString(),
        } as Record<string, unknown>)
        .eq("stripe_customer_id", customerId);

      if (error) {
        console.error("Error updating profile:", error);
        throw new Error(`Failed to update profile: ${error.message}`);
      }

      console.log(`Updated subscription for customer ${customerId}: ${plan} (${status})`);
      break;
    }

    case "customer.subscription.deleted": {
      const customerId = object.customer as string;

      // Reset user to free plan
      const { error } = await supabaseClient
        .from("profiles")
        .update({
          plan: "free",
          updated_at: new Date().toISOString(),
        } as Record<string, unknown>)
        .eq("stripe_customer_id", customerId);

      if (error) {
        console.error("Error updating profile:", error);
        throw new Error(`Failed to update profile: ${error.message}`);
      }

      console.log(`Cancelled subscription for customer ${customerId}`);
      break;
    }

    case "invoice.paid": {
      const customerId = object.customer as string;
      const amountPaid = (object.amount_paid as number) || 0;
      const currency = (object.currency as string) || "usd";

      // Record payment or add credits
      // This could also trigger partner revenue share calculations
      console.log(`Invoice paid: ${amountPaid} ${currency} for customer ${customerId}`);
      
      // You might want to update credits or billing cycles here
      break;
    }

    case "checkout.session.completed": {
      const customerId = object.customer as string;
      const metadata = (object.metadata as Record<string, string>) || {};
      const plan = metadata.plan || "free";
      const userId = metadata.user_id;

      if (userId) {
        // Update user profile with plan and customer ID
        const { error } = await supabaseClient
          .from("profiles")
          .update({
            plan: plan,
            stripe_customer_id: customerId,
            updated_at: new Date().toISOString(),
          } as Record<string, unknown>)
          .eq("id", userId);

        if (error) {
          console.error("Error updating profile:", error);
        } else {
          console.log(`Checkout completed: user ${userId} subscribed to ${plan}`);
        }
      }
      break;
    }

    default:
      console.log(`Unhandled event type: ${type}`);
  }
}

Deno.serve(async (request) => {
  // Handle CORS preflight
  const corsPreflightResponse = handleCors(request);
  if (corsPreflightResponse) return corsPreflightResponse;

  try {
    const config = getSupabaseConfig();
    const stripeConfig = getStripeConfig();

    // Get webhook payload
    const payload = await request.text();
    const signature = request.headers.get("stripe-signature");

    // Verify webhook signature in production
    if (stripeConfig.webhookSecret) {
      const isValid = await verifyStripeSignature(
        payload,
        signature,
        stripeConfig.webhookSecret
      );

      if (!isValid) {
        console.error("Invalid webhook signature");
        return corsResponse(
          { error: "Invalid signature" },
          401,
          request.headers.get("origin")
        );
      }
    }

    // Parse webhook event
    const event: StripeWebhookEvent = JSON.parse(payload);

    // Create Supabase client with service role for admin operations
    const supabaseClient = createClient(
      config.url,
      config.serviceRoleKey || config.anonKey
    );

    // Process the webhook event
    await processWebhookEvent(event, supabaseClient);

    // Return success response to Stripe
    return successResponse(
      { received: true, eventId: event.id },
      "Webhook processed successfully",
      request
    );
  } catch (error) {
    return handleError(error, request);
  }
});
