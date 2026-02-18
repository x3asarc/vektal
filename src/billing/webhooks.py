"""
Stripe webhook handlers.

CRITICAL: This is where USER ACCOUNTS ARE CREATED.
Per CONTEXT.md line 70-72: "Payment succeeds -> CREATE User account"

Handles:
- checkout.session.completed: CREATE user account after successful payment
- customer.subscription.updated: Update user tier after subscription change
- invoice.payment_failed: Suspend account on payment failure

CRITICAL: Always verify webhook signature to prevent spoofing.
"""
from flask import Blueprint, request, jsonify, current_app
import stripe
import os
from datetime import datetime, timedelta
from src.models import db
from src.models.user import User, UserTier, AccountStatus
from src.billing.stripe_client import get_tier_from_price_id
from src.auth.email_verification import generate_verification_token, generate_verification_url
from src.auth.email_sender import send_verification_email, send_welcome_email

webhooks_bp = Blueprint('webhooks', __name__)

# Stripe webhook secret for signature verification
WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')


def verify_stripe_signature(payload: bytes, sig_header: str) -> dict:
    """
    Verify Stripe webhook signature.

    Returns:
        Stripe event dict if valid, None if invalid
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
        return event
    except ValueError as e:
        current_app.logger.error(f'Invalid webhook payload: {e}')
        return None
    except stripe.error.SignatureVerificationError as e:
        current_app.logger.error(f'Invalid webhook signature: {e}')
        return None


@webhooks_bp.route('/stripe', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events.

    CRITICAL: Verify signature before processing.
    """
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    if not sig_header:
        return jsonify({'error': 'Missing signature'}), 400

    event = verify_stripe_signature(payload, sig_header)
    if not event:
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle different event types
    event_type = event['type']
    data = event['data']['object']

    # Check for duplicate events (idempotency)
    event_id = event['id']
    _ = event_id
    # TODO: Store processed event IDs in Redis with TTL to prevent replay attacks

    try:
        if event_type == 'checkout.session.completed':
            handle_checkout_completed(data)

        elif event_type == 'customer.subscription.updated':
            handle_subscription_updated(data)

        elif event_type == 'customer.subscription.deleted':
            handle_subscription_deleted(data)

        elif event_type == 'invoice.payment_failed':
            handle_payment_failed(data)

        elif event_type == 'invoice.paid':
            handle_invoice_paid(data)

        else:
            current_app.logger.info(f'Unhandled webhook event: {event_type}')

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        current_app.logger.error(f'Webhook processing error: {str(e)}')
        # Return 200 to prevent Stripe from retrying
        # Log error for investigation
        return jsonify({'status': 'error', 'message': str(e)}), 200


def handle_checkout_completed(session: dict):
    """
    Handle successful checkout session.

    THIS IS WHERE USER ACCOUNTS ARE CREATED.
    Per CONTEXT.md: "Payment succeeds -> CREATE User account"

    Flow:
    1. Extract email, tier, password_hash from metadata
    2. Create User with PENDING_OAUTH status
    3. Generate email verification token
    4. Send verification email + welcome email
    """
    metadata = session.get('metadata', {})
    email = session.get('customer_email') or metadata.get('email')
    tier_value = metadata.get('tier', 'tier_1')
    password_hash = metadata.get('password_hash')
    customer_id = session.get('customer')
    subscription_id = session.get('subscription')

    if not email:
        current_app.logger.error('Checkout completed without email')
        return

    if not password_hash:
        current_app.logger.error('Checkout completed without password_hash - cannot create account')
        return

    # Map tier string to enum
    tier_map = {
        'tier_1': UserTier.TIER_1,
        'tier_2': UserTier.TIER_2,
        'tier_3': UserTier.TIER_3,
    }
    tier = tier_map.get(tier_value, UserTier.TIER_1)

    # Check if user already exists (idempotency - webhook might be retried)
    user = User.query.filter_by(email=email).first()

    if user:
        # Update existing user with Stripe info (retry scenario)
        user.stripe_customer_id = customer_id
        user.stripe_subscription_id = subscription_id
        user.tier = tier
        current_app.logger.info(f'Updated existing user {email} with Stripe subscription')
    else:
        # CREATE NEW USER - This is the main registration path
        user = User(
            email=email,
            password_hash=password_hash,  # Already hashed in checkout
            tier=tier,
            account_status=AccountStatus.PENDING_OAUTH,
            email_verified=False,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            oauth_completion_deadline=datetime.utcnow() + timedelta(days=7),
            billing_period_start=datetime.utcnow(),
            billing_period_end=datetime.utcnow() + timedelta(days=30)
        )

        db.session.add(user)
        current_app.logger.info(f'CREATED new user {email} from Stripe checkout')

    # Get subscription item ID for future modifications
    if subscription_id:
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            user.stripe_subscription_item_id = subscription['items']['data'][0]['id']
        except Exception as e:
            current_app.logger.warning(f'Could not retrieve subscription details: {e}')

    db.session.commit()

    # Generate and store email verification token
    try:
        verification_url = generate_verification_url(email)
        token = generate_verification_token(email)
        user.email_verification_token = token
        db.session.commit()

        # Send verification email
        send_verification_email(email, verification_url)
        current_app.logger.info(f'Verification email sent to {email}')

        # Send welcome email
        dashboard_url = os.getenv('APP_URL', 'http://localhost:5000') + '/dashboard'
        send_welcome_email(email, dashboard_url)
        current_app.logger.info(f'Welcome email sent to {email}')

    except Exception as e:
        current_app.logger.warning(f'Could not send emails to {email}: {e}')


def handle_subscription_updated(subscription: dict):
    """
    Handle subscription update (tier change).

    Updates user tier based on new price.
    """
    customer_id = subscription.get('customer')
    if not customer_id:
        return

    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        current_app.logger.warning(f'Subscription update for unknown customer: {customer_id}')
        return

    # Get new price ID
    items = subscription.get('items', {}).get('data', [])
    if not items:
        return

    new_price_id = items[0].get('price', {}).get('id')
    new_tier = get_tier_from_price_id(new_price_id)

    if new_tier and new_tier != user.tier:
        old_tier = user.tier
        user.tier = new_tier

        # Clear pending tier if this was a scheduled change
        if user.pending_tier == new_tier:
            user.pending_tier = None
            user.tier_change_effective_date = None

        db.session.commit()
        current_app.logger.info(f'User {user.email} tier changed: {old_tier.value} -> {new_tier.value}')

    # Update billing period
    user.billing_period_start = datetime.fromtimestamp(subscription['current_period_start'])
    user.billing_period_end = datetime.fromtimestamp(subscription['current_period_end'])
    db.session.commit()


def handle_subscription_deleted(subscription: dict):
    """
    Handle subscription cancellation.

    Suspends user account when subscription is fully cancelled.
    """
    customer_id = subscription.get('customer')
    if not customer_id:
        return

    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        return

    user.account_status = AccountStatus.SUSPENDED
    user.stripe_subscription_id = None
    user.stripe_subscription_item_id = None
    db.session.commit()

    current_app.logger.info(f'User {user.email} subscription cancelled, account suspended')

    # TODO: Send cancellation email via Celery


def handle_payment_failed(invoice: dict):
    """
    Handle failed payment.

    Sends warning on first failure, suspends on continued failure.
    """
    customer_id = invoice.get('customer')
    if not customer_id:
        return

    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        return

    attempt_count = invoice.get('attempt_count', 1)

    if attempt_count >= 3:
        # Suspend account after 3 failed attempts
        user.account_status = AccountStatus.SUSPENDED
        db.session.commit()
        current_app.logger.warning(f'User {user.email} account suspended due to payment failure')
        # TODO: Send suspension email
    else:
        # Log warning, Stripe will retry
        current_app.logger.info(f'Payment failed for {user.email}, attempt {attempt_count}')
        # TODO: Send payment failure warning email


def handle_invoice_paid(invoice: dict):
    """
    Handle successful invoice payment.

    Reactivates suspended accounts after successful payment.
    """
    customer_id = invoice.get('customer')
    if not customer_id:
        return

    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    if not user:
        return

    # Reactivate if was suspended due to payment failure
    if user.account_status == AccountStatus.SUSPENDED:
        # Check if user has completed OAuth
        from src.models.shopify import ShopifyStore
        store = ShopifyStore.query.filter_by(user_id=user.id).first()

        if store and store.is_active:
            user.account_status = AccountStatus.ACTIVE
        else:
            user.account_status = AccountStatus.PENDING_OAUTH

        db.session.commit()
        current_app.logger.info(f'User {user.email} reactivated after successful payment')
