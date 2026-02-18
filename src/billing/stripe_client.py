"""
Stripe API client for checkout session creation.

Environment variables required:
- STRIPE_SECRET_KEY: Stripe API secret key
- STRIPE_PRICE_TIER_1: Stripe Price ID for Tier 1
- STRIPE_PRICE_TIER_2: Stripe Price ID for Tier 2
- STRIPE_PRICE_TIER_3: Stripe Price ID for Tier 3

NOTE: User creation happens in webhook (Plan 04b), NOT here.
Per CONTEXT.md: "Payment succeeds -> CREATE User account"
"""
import stripe
import os
from typing import Dict, Optional
from src.models.user import UserTier

# Initialize Stripe with secret key
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')


def get_tier_price_id(tier: UserTier) -> str:
    """
    Get Stripe Price ID for a tier.

    Args:
        tier: UserTier enum value

    Returns:
        Stripe Price ID string

    Note: These should be set in environment variables after creating
    Products/Prices in Stripe Dashboard.
    """
    tier_prices = {
        UserTier.TIER_1: os.getenv('STRIPE_PRICE_TIER_1', 'price_tier1_monthly'),
        UserTier.TIER_2: os.getenv('STRIPE_PRICE_TIER_2', 'price_tier2_monthly'),
        UserTier.TIER_3: os.getenv('STRIPE_PRICE_TIER_3', 'price_tier3_monthly'),
    }
    return tier_prices.get(tier)


def get_tier_from_price_id(price_id: str) -> Optional[UserTier]:
    """
    Get UserTier from Stripe Price ID.

    Args:
        price_id: Stripe Price ID

    Returns:
        UserTier enum value or None if not found
    """
    price_to_tier = {
        os.getenv('STRIPE_PRICE_TIER_1', 'price_tier1_monthly'): UserTier.TIER_1,
        os.getenv('STRIPE_PRICE_TIER_2', 'price_tier2_monthly'): UserTier.TIER_2,
        os.getenv('STRIPE_PRICE_TIER_3', 'price_tier3_monthly'): UserTier.TIER_3,
    }
    return price_to_tier.get(price_id)


def create_checkout_session(
    email: str,
    password: str,
    tier: UserTier,
    success_url: str,
    cancel_url: str
) -> Dict:
    """
    Create Stripe Checkout session for new subscription.

    IMPORTANT: This does NOT create a user. User creation happens
    in the Stripe webhook when payment succeeds (Plan 04b).

    Args:
        email: Customer email (pre-filled in checkout)
        password: Password to store (hashed) when user is created in webhook
        tier: Selected tier
        success_url: Redirect URL on successful payment
        cancel_url: Redirect URL on cancelled payment

    Returns:
        Dict with checkout session ID and URL
    """
    try:
        price_id = get_tier_price_id(tier)
        if not price_id:
            return {'success': False, 'error': f'Invalid tier: {tier}'}

        # Hash password before storing in metadata
        # (Stripe metadata is visible in dashboard - use hashed value)
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        session = stripe.checkout.Session.create(
            mode='subscription',
            payment_method_types=['card'],
            customer_email=email,
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            # Pass email, tier, and HASHED password in metadata for webhook processing
            # Webhook will create user with these details
            metadata={
                'email': email,
                'tier': tier.value,
                'password_hash': password_hash  # Already hashed for security
            },
            # Allow customer to update payment method
            payment_method_collection='always',
            # Collect billing address for tax compliance
            billing_address_collection='required'
        )

        return {
            'success': True,
            'session_id': session.id,
            'checkout_url': session.url
        }

    except stripe.error.StripeError as e:
        return {'success': False, 'error': str(e)}
