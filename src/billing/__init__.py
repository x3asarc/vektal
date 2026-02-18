"""
Billing module for Stripe subscription management.

Provides:
- Checkout session creation for new subscriptions
- Webhook handling for payment events (including USER CREATION)
- Subscription modification (upgrades/downgrades)
"""
from src.billing.stripe_client import (
    create_checkout_session,
    get_tier_price_id,
    get_tier_from_price_id
)
from src.billing.checkout import checkout_bp
from src.billing.webhooks import webhooks_bp
from src.billing.subscription import (
    upgrade_subscription,
    downgrade_subscription,
    cancel_pending_downgrade,
    cancel_subscription
)
from src.billing.routes import billing_bp

__all__ = [
    'create_checkout_session',
    'get_tier_price_id',
    'get_tier_from_price_id',
    'checkout_bp',
    'webhooks_bp',
    'billing_bp',
    'upgrade_subscription',
    'downgrade_subscription',
    'cancel_pending_downgrade',
    'cancel_subscription'
]
