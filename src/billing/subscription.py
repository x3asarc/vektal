"""
Subscription modification functions for tier upgrades/downgrades.

Per CONTEXT.md:
- Upgrades: Immediate effect with prorated billing
- Downgrades: Scheduled for end of billing cycle (no refunds)
"""
import stripe
import os
from flask import current_app
from datetime import datetime
from typing import Dict
from src.models import db
from src.models.user import User, UserTier, AccountStatus
from src.billing.stripe_client import get_tier_price_id

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')


def upgrade_subscription(user_id: int, new_tier: UserTier) -> Dict:
    """
    Upgrade user subscription with immediate billing.

    Stripe automatically calculates proration:
    - Credit for unused time on old plan
    - Charge for remaining time on new plan

    Args:
        user_id: User ID
        new_tier: New tier to upgrade to

    Returns:
        Dict with success status and subscription info
    """
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'error': 'User not found'}

    if not user.stripe_subscription_id:
        return {'success': False, 'error': 'No active subscription'}

    # Check if actually an upgrade
    tier_levels = {UserTier.TIER_1: 1, UserTier.TIER_2: 2, UserTier.TIER_3: 3}
    if tier_levels.get(new_tier, 0) <= tier_levels.get(user.tier, 0):
        return {'success': False, 'error': 'Use downgrade endpoint for downgrades'}

    new_price_id = get_tier_price_id(new_tier)
    if not new_price_id:
        return {'success': False, 'error': f'Invalid tier: {new_tier}'}

    try:
        # Get current subscription
        subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)

        # Update subscription (Stripe automatically prorates)
        updated_subscription = stripe.Subscription.modify(
            user.stripe_subscription_id,
            items=[{
                'id': subscription['items']['data'][0]['id'],
                'price': new_price_id,
            }],
            proration_behavior='create_prorations',  # Immediate proration
            billing_cycle_anchor='unchanged',  # Keep existing billing date
        )

        # Update user tier immediately
        user.tier = new_tier
        user.stripe_subscription_item_id = updated_subscription['items']['data'][0]['id']
        db.session.commit()

        return {
            'success': True,
            'message': f'Upgraded to {new_tier.value}',
            'subscription_id': updated_subscription.id
        }

    except stripe.error.StripeError as e:
        db.session.rollback()
        current_app.logger.error(f'Stripe upgrade error: {str(e)}')
        return {'success': False, 'error': str(e)}


def downgrade_subscription(user_id: int, new_tier: UserTier) -> Dict:
    """
    Schedule subscription downgrade for end of billing cycle.

    Per CONTEXT.md: Downgrades take effect at end of billing period (no refunds).

    Args:
        user_id: User ID
        new_tier: New tier to downgrade to

    Returns:
        Dict with success status and effective date
    """
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'error': 'User not found'}

    if not user.stripe_subscription_id:
        return {'success': False, 'error': 'No active subscription'}

    # Check if actually a downgrade
    tier_levels = {UserTier.TIER_1: 1, UserTier.TIER_2: 2, UserTier.TIER_3: 3}
    if tier_levels.get(new_tier, 0) >= tier_levels.get(user.tier, 0):
        return {'success': False, 'error': 'Use upgrade endpoint for upgrades'}

    new_price_id = get_tier_price_id(new_tier)
    if not new_price_id:
        return {'success': False, 'error': f'Invalid tier: {new_tier}'}

    try:
        # Get current subscription to find billing period end
        subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)

        # Store pending tier change in database
        user.pending_tier = new_tier
        user.tier_change_effective_date = datetime.fromtimestamp(
            subscription['current_period_end']
        )
        db.session.commit()

        # Schedule price change for next billing cycle (no proration = no refund)
        stripe.Subscription.modify(
            user.stripe_subscription_id,
            items=[{
                'id': subscription['items']['data'][0]['id'],
                'price': new_price_id,
            }],
            proration_behavior='none',  # NO prorations (no refunds)
            billing_cycle_anchor='unchanged',
        )

        return {
            'success': True,
            'message': f'Downgrade to {new_tier.value} scheduled',
            'effective_date': user.tier_change_effective_date.isoformat(),
            'current_tier': user.tier.value
        }

    except stripe.error.StripeError as e:
        db.session.rollback()
        current_app.logger.error(f'Stripe downgrade error: {str(e)}')
        return {'success': False, 'error': str(e)}


def cancel_pending_downgrade(user_id: int) -> Dict:
    """
    Cancel a pending subscription downgrade.

    User can cancel a scheduled downgrade before it takes effect.
    """
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'error': 'User not found'}

    if not user.pending_tier:
        return {'success': False, 'error': 'No pending downgrade'}

    try:
        # Revert subscription to current tier price
        subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
        current_price_id = get_tier_price_id(user.tier)

        stripe.Subscription.modify(
            user.stripe_subscription_id,
            items=[{
                'id': subscription['items']['data'][0]['id'],
                'price': current_price_id,
            }],
            proration_behavior='none',
        )

        # Clear pending tier
        user.pending_tier = None
        user.tier_change_effective_date = None
        db.session.commit()

        return {
            'success': True,
            'message': 'Downgrade cancelled',
            'current_tier': user.tier.value
        }

    except stripe.error.StripeError as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}


def cancel_subscription(user_id: int, at_period_end: bool = True) -> Dict:
    """
    Cancel user subscription.

    Args:
        user_id: User ID
        at_period_end: If True, cancel at end of billing period. If False, cancel immediately.
    """
    user = User.query.get(user_id)
    if not user:
        return {'success': False, 'error': 'User not found'}

    if not user.stripe_subscription_id:
        return {'success': False, 'error': 'No active subscription'}

    try:
        if at_period_end:
            # Schedule cancellation for end of billing period
            subscription = stripe.Subscription.modify(
                user.stripe_subscription_id,
                cancel_at_period_end=True
            )
            return {
                'success': True,
                'message': 'Subscription will cancel at end of billing period',
                'cancel_at': datetime.fromtimestamp(subscription['current_period_end']).isoformat()
            }
        else:
            # Cancel immediately
            stripe.Subscription.cancel(user.stripe_subscription_id)
            user.stripe_subscription_id = None
            user.account_status = AccountStatus.SUSPENDED
            db.session.commit()
            return {
                'success': True,
                'message': 'Subscription cancelled immediately'
            }

    except stripe.error.StripeError as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}
