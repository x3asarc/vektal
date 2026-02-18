"""
Checkout API endpoint for initiating Stripe Checkout.

This endpoint handles the FIRST step of registration:
1. User provides email, password, and selected tier
2. Stripe Checkout session is created
3. User is redirected to Stripe to pay
4. On payment success, webhook creates user account (Plan 04b)

Per CONTEXT.md line 70-72: "Payment succeeds -> CREATE User account"
"""
from flask import Blueprint, request, jsonify
from src.billing.stripe_client import create_checkout_session
from src.models.user import User, UserTier
import re
import os

checkout_bp = Blueprint('checkout', __name__)


def validate_email(email: str) -> tuple:
    """
    Validate email format.

    Returns:
        (is_valid: bool, error_message: str or None)
    """
    if not email:
        return False, 'Email is required'

    # Basic email regex (covers 99% of valid emails)
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return False, 'Invalid email format'

    if len(email) > 255:
        return False, 'Email too long (max 255 characters)'

    return True, None


def validate_password(password: str) -> tuple:
    """
    Validate password strength.

    Per CONTEXT.md: Minimum 8 characters, no complexity rules (NIST standard).

    Returns:
        (is_valid: bool, error_message: str or None)
    """
    if not password:
        return False, 'Password is required'

    if len(password) < 8:
        return False, 'Password must be at least 8 characters'

    if len(password) > 128:
        return False, 'Password too long (max 128 characters)'

    return True, None


@checkout_bp.route('/plans', methods=['GET'])
def list_plans():
    """
    List available subscription plans.

    Returns pricing info for frontend display.
    """
    plans = [
        {
            'tier': 'tier_1',
            'name': 'Starter',
            'price': os.getenv('TIER_1_PRICE', '$29'),
            'period': 'month',
            'features': [
                'Basic product updates',
                'Up to 100 products/month',
                'Email support'
            ]
        },
        {
            'tier': 'tier_2',
            'name': 'Professional',
            'price': os.getenv('TIER_2_PRICE', '$99'),
            'period': 'month',
            'features': [
                'AI-powered descriptions',
                'Up to 1,000 products/month',
                'Priority support',
                'Bulk operations'
            ]
        },
        {
            'tier': 'tier_3',
            'name': 'Enterprise',
            'price': os.getenv('TIER_3_PRICE', '$299'),
            'period': 'month',
            'features': [
                'Full Claude agents',
                'Unlimited products',
                'Dedicated support',
                'Custom integrations',
                'Advanced analytics'
            ]
        }
    ]
    return jsonify({'plans': plans}), 200


@checkout_bp.route('/create', methods=['POST'])
def create_checkout():
    """
    Create Stripe Checkout session.

    This is the REGISTRATION entry point. User provides:
    - email
    - password (will be hashed)
    - tier selection

    User account is NOT created here. It's created by Stripe webhook
    after payment succeeds (Plan 04b).

    Request body:
    {
        "email": "user@example.com",
        "password": "securepassword123",
        "tier": "tier_2"  // tier_1, tier_2, or tier_3
    }

    Returns:
        200: Checkout session URL
        400: Invalid request
        409: Email already registered
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    tier_value = data.get('tier', 'tier_1')

    # Validate email
    is_valid, error = validate_email(email)
    if not is_valid:
        return jsonify({'error': error}), 400

    # Validate password
    is_valid, error = validate_password(password)
    if not is_valid:
        return jsonify({'error': error}), 400

    # Check if email already registered
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'Email already registered'}), 409

    # Map tier string to enum
    tier_map = {
        'tier_1': UserTier.TIER_1,
        'tier_2': UserTier.TIER_2,
        'tier_3': UserTier.TIER_3,
    }
    tier = tier_map.get(tier_value)
    if not tier:
        return jsonify({'error': f'Invalid tier: {tier_value}'}), 400

    # Build success/cancel URLs
    base_url = request.host_url.rstrip('/')
    success_url = f"{base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}/billing/cancelled"

    result = create_checkout_session(email, password, tier, success_url, cancel_url)

    if result['success']:
        return jsonify({
            'checkout_url': result['checkout_url'],
            'session_id': result['session_id']
        }), 200
    else:
        return jsonify({'error': result['error']}), 400


@checkout_bp.route('/check-email', methods=['POST'])
def check_email():
    """
    Check if email is available for registration.

    Useful for real-time validation in registration form.

    Request body:
    {
        "email": "user@example.com"
    }

    Returns:
        200: {"available": true/false}
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    email = data.get('email', '').strip().lower()

    # Validate format first
    is_valid, error = validate_email(email)
    if not is_valid:
        return jsonify({'available': False, 'error': error}), 200

    # Check if exists
    existing = User.query.filter_by(email=email).first()
    return jsonify({'available': existing is None}), 200


@checkout_bp.route('/success', methods=['GET'])
def checkout_success():
    """
    Checkout success page.

    User is redirected here after successful Stripe payment.
    Webhook creates the account, this page shows next steps.
    """
    session_id = request.args.get('session_id')
    return jsonify({
        'success': True,
        'message': 'Payment successful! Your account is being created.',
        'next_steps': [
            'Check your email for login instructions',
            'Verify your email address',
            'Connect your Shopify store'
        ],
        'note': 'You will receive an email shortly with your login link.',
        'session_id': session_id
    }), 200


@checkout_bp.route('/cancelled', methods=['GET'])
def checkout_cancelled():
    """Checkout cancelled page."""
    return jsonify({
        'success': False,
        'message': 'Checkout was cancelled. No charges were made.',
        'retry_url': '/billing/plans'
    }), 200
