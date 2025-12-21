/**
 * Checkout utility functions for Stripe integration
 */

export interface CheckoutRequest {
  plan: string;
  partner_code?: string;
}

export interface CheckoutResponse {
  checkout_url: string;
  session_id: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function startCheckout(plan: string, partnerCode?: string): Promise<string> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/billing/checkout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // In production, include auth token
        // "Authorization": `Bearer ${getAuthToken()}`,
      },
      body: JSON.stringify({
        plan,
        partner_code: partnerCode,
      } as CheckoutRequest),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Failed to create checkout session");
    }

    const data: CheckoutResponse = await response.json();
    return data.checkout_url;
  } catch (error) {
    console.error("Checkout error:", error);
    throw error;
  }
}

export async function getUsage() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/billing/usage`, {
      headers: {
        // In production, include auth token
        // "Authorization": `Bearer ${getAuthToken()}`,
      },
    });

    if (!response.ok) {
      throw new Error("Failed to fetch usage");
    }

    return await response.json();
  } catch (error) {
    console.error("Usage fetch error:", error);
    throw error;
  }
}

export async function getCredits() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/billing/credits`, {
      headers: {
        // In production, include auth token
        // "Authorization": `Bearer ${getAuthToken()}`,
      },
    });

    if (!response.ok) {
      throw new Error("Failed to fetch credits");
    }

    return await response.json();
  } catch (error) {
    console.error("Credits fetch error:", error);
    throw error;
  }
}


