"""
Stripe Subscription Integration
"""
import os
import logging
from typing import Optional, Dict, Any
import stripe

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")


def create_subscription(customer_id: str, price_id: str) -> Dict[str, Any]:
    """
    Create a Stripe subscription.
    Returns subscription object with invoice details.
    """
    try:
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            expand=["latest_invoice.payment_intent"],
        )
        return subscription
    except stripe.error.StripeError as e:
        logger.error(f"Stripe subscription creation failed: {str(e)}")
        raise


def create_checkout_session(
    customer_id: Optional[str],
    price_id: str,
    success_url: str,
    cancel_url: str,
    metadata: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create a Stripe Checkout session for one-time or subscription payments.
    """
    try:
        session_params = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": cancel_url,
        }
        
        if customer_id:
            session_params["customer"] = customer_id
        
        if metadata:
            session_params["metadata"] = metadata
        
        session = stripe.checkout.Session.create(**session_params)
        return session
    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout session creation failed: {str(e)}")
        raise


def create_customer(email: str, metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Create a Stripe customer."""
    try:
        customer_params = {"email": email}
        if metadata:
            customer_params["metadata"] = metadata
        
        customer = stripe.Customer.create(**customer_params)
        return customer
    except stripe.error.StripeError as e:
        logger.error(f"Stripe customer creation failed: {str(e)}")
        raise


def report_usage(
    subscription_item_id: str,
    quantity: int,
    timestamp: Optional[int] = None
) -> Dict[str, Any]:
    """
    Report metered usage to Stripe for overage billing.
    """
    try:
        import time
        usage_record = stripe.UsageRecord.create(
            subscription_item=subscription_item_id,
            quantity=quantity,
            timestamp=timestamp or int(time.time()),
        )
        return usage_record
    except stripe.error.StripeError as e:
        logger.error(f"Stripe usage record creation failed: {str(e)}")
        raise


def handle_webhook(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle Stripe webhook events.
    Returns response dict indicating success/failure.
    """
    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})
    
    try:
        if event_type == "invoice.paid":
            # Handle successful payment
            customer_id = data.get("customer")
            amount_paid = data.get("amount_paid", 0) / 100  # Convert from cents
            invoice_id = data.get("id")
            
            return {
                "status": "success",
                "event": event_type,
                "customer_id": customer_id,
                "amount": amount_paid,
                "invoice_id": invoice_id,
            }
        
        elif event_type == "customer.subscription.updated":
            # Handle subscription changes
            customer_id = data.get("customer")
            status = data.get("status")
            
            return {
                "status": "success",
                "event": event_type,
                "customer_id": customer_id,
                "subscription_status": status,
            }
        
        elif event_type == "customer.subscription.deleted":
            # Handle subscription cancellation
            customer_id = data.get("customer")
            
            return {
                "status": "success",
                "event": event_type,
                "customer_id": customer_id,
            }
        
        else:
            return {
                "status": "ignored",
                "event": event_type,
                "message": f"Event type {event_type} not handled",
            }
    
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "event": event_type,
            "error": str(e),
        }

