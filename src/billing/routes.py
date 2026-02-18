"""
Billing API routes for subscription management.

Provides logged-in users with:
- GET /billing/subscription: Get current subscription status
- POST /billing/upgrade: Upgrade subscription (immediate)
- POST /billing/downgrade: Downgrade subscription (scheduled)
- POST /billing/cancel-downgrade: Cancel pending downgrade
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from src.billing.subscription import (
    upgrade_subscription,
    downgrade_subscription,
    cancel_pending_downgrade
)
from src.models.user import UserTier
from src.auth.decorators import email_verified_required

billing_bp = Blueprint('billing', __name__)


@billing_bp.route('/subscription', methods=['GET'])
@login_required
def get_subscription():
    """
    Get current subscription status.

    Returns tier, billing period, and any pending changes.
    """
    return jsonify({
        'tier': current_user.tier.value,
        'billing_period_start': current_user.billing_period_start.isoformat() if current_user.billing_period_start else None,
        'billing_period_end': current_user.billing_period_end.isoformat() if current_user.billing_period_end else None,
        'pending_tier': current_user.pending_tier.value if current_user.pending_tier else None,
        'tier_change_effective_date': current_user.tier_change_effective_date.isoformat() if current_user.tier_change_effective_date else None,
        'stripe_customer_id': current_user.stripe_customer_id,
        'has_active_subscription': current_user.stripe_subscription_id is not None
    }), 200


@billing_bp.route('/upgrade', methods=['POST'])
@login_required
@email_verified_required
def upgrade():
    """
    Upgrade subscription.

    Request body:
    {
        "tier": "tier_3"  // Must be higher than current tier
    }

    Returns:
        200: Upgrade successful (immediate effect)
        400: Invalid tier or not an upgrade
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    tier_value = data.get('tier')
    tier_map = {
        'tier_1': UserTier.TIER_1,
        'tier_2': UserTier.TIER_2,
        'tier_3': UserTier.TIER_3,
    }
    new_tier = tier_map.get(tier_value)

    if not new_tier:
        return jsonify({'error': f'Invalid tier: {tier_value}'}), 400

    result = upgrade_subscription(current_user.id, new_tier)

    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({'error': result['error']}), 400


@billing_bp.route('/downgrade', methods=['POST'])
@login_required
@email_verified_required
def downgrade():
    """
    Schedule subscription downgrade.

    Request body:
    {
        "tier": "tier_1"  // Must be lower than current tier
    }

    Returns:
        200: Downgrade scheduled (takes effect at end of billing period)
        400: Invalid tier or not a downgrade
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    tier_value = data.get('tier')
    tier_map = {
        'tier_1': UserTier.TIER_1,
        'tier_2': UserTier.TIER_2,
        'tier_3': UserTier.TIER_3,
    }
    new_tier = tier_map.get(tier_value)

    if not new_tier:
        return jsonify({'error': f'Invalid tier: {tier_value}'}), 400

    result = downgrade_subscription(current_user.id, new_tier)

    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({'error': result['error']}), 400


@billing_bp.route('/cancel-downgrade', methods=['POST'])
@login_required
def cancel_downgrade():
    """
    Cancel pending downgrade.

    User can cancel a scheduled downgrade before it takes effect.
    """
    result = cancel_pending_downgrade(current_user.id)

    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify({'error': result['error']}), 400
