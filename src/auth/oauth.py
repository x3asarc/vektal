"""
Shopify OAuth integration with retry logic and error handling.

Flow per CONTEXT.md:
1. User clicks "Connect Shopify Store" (after payment + email verification)
2. Generate state token, store in Redis session, redirect to Shopify
3. User authorizes app in Shopify admin
4. Shopify redirects to callback with code
5. Exchange code for access token (with exponential backoff)
6. Store encrypted token, update account status to ACTIVE

Error handling:
- access_denied: Show friendly message, allow retry
- network_error: Automatic retry with backoff, then show retry button
- state_mismatch: Security error, require fresh OAuth start
"""
from flask import Blueprint, request, jsonify, session, redirect, url_for, current_app
from flask_login import login_required, current_user, login_user
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import os
from datetime import datetime

from src.models import db
from src.models.user import AccountStatus
from src.models.shopify import ShopifyStore
from src.models.oauth_attempt import OAuthAttempt
from src.auth.decorators import email_verified_required
from src.core.secrets import get_secret
from src.core.tenancy.provisioning import provision_tenant_schema

oauth_bp = Blueprint('oauth', __name__)

# Shopify OAuth configuration
SHOPIFY_API_KEY = get_secret('SHOPIFY_API_KEY') or os.getenv('SHOPIFY_CLIENT_ID')
SHOPIFY_API_SECRET = get_secret('SHOPIFY_API_SECRET') or os.getenv('SHOPIFY_CLIENT_SECRET')
SHOPIFY_API_SCOPES = 'read_products,write_products,read_inventory,write_inventory,read_locations,write_files'
APP_URL = os.getenv('APP_URL', 'http://localhost:5000')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')


def generate_state_token() -> str:
    """Generate cryptographically secure state token for CSRF protection."""
    return os.urandom(16).hex()


def _resolve_pending_oauth_attempt(state_token: str | None, shop: str | None) -> OAuthAttempt | None:
    """
    Resolve a pending, non-expired OAuth attempt for state-recovery scenarios.

    This is used only when callback session state is missing/mismatched.
    """
    if not state_token:
        return None

    attempt = OAuthAttempt.query.filter_by(state_token=state_token).first()
    if not attempt:
        return None

    if attempt.result != 'pending':
        return None

    if attempt.expires_at and attempt.expires_at < datetime.utcnow():
        return None

    if shop and attempt.shop_domain.lower() != shop.lower():
        return None

    return attempt


@oauth_bp.route('/shopify', methods=['GET'])
@login_required
@email_verified_required
def initiate_shopify_oauth():
    """
    Initiate Shopify OAuth flow.

    Query params:
        shop: Shopify store domain (e.g., my-store.myshopify.com)

    Requires: User logged in with verified email
    """
    shop = request.args.get('shop')

    if not shop:
        return jsonify({
            'error': 'Missing shop parameter',
            'message': 'Please enter your Shopify store domain'
        }), 400

    # Normalize shop domain
    shop = shop.strip().lower()
    if not shop.endswith('.myshopify.com'):
        shop = f"{shop}.myshopify.com"

    # Validate shop format (basic check)
    if not shop.replace('.myshopify.com', '').replace('-', '').isalnum():
        return jsonify({
            'error': 'Invalid shop domain',
            'message': 'Shop domain must contain only letters, numbers, and hyphens'
        }), 400

    # Check if user already has a connected store
    existing_store = ShopifyStore.query.filter_by(user_id=current_user.id).first()
    if existing_store and existing_store.shop_domain != shop:
        return jsonify({
            'error': 'Store already connected',
            'message': f'Your account is already connected to {existing_store.shop_domain}. Disconnect first to connect a different store.'
        }), 400

    # Generate state token and store in session
    state = generate_state_token()
    session['oauth_state'] = state
    session['oauth_shop'] = shop

    # Create OAuth attempt record
    OAuthAttempt.create_attempt(
        user_id=current_user.id,
        shop_domain=shop,
        state_token=state,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:512] if request.user_agent else None
    )

    # Increment user's OAuth attempt counter
    current_user.oauth_attempts += 1
    current_user.last_oauth_attempt = datetime.utcnow()
    db.session.commit()

    # Build authorization URL
    redirect_uri = f"{APP_URL}/oauth/callback"
    auth_url = (
        f"https://{shop}/admin/oauth/authorize?"
        f"client_id={SHOPIFY_API_KEY}&"
        f"scope={SHOPIFY_API_SCOPES}&"
        f"redirect_uri={redirect_uri}&"
        f"state={state}"
    )

    # For API requests, return URL; for browser, redirect
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            'auth_url': auth_url,
            'state': state
        }), 200
    else:
        return redirect(auth_url)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((requests.exceptions.Timeout, requests.exceptions.ConnectionError)),
    reraise=True
)
def exchange_code_for_token(shop: str, code: str) -> str:
    """
    Exchange OAuth code for access token with retry logic.

    Retries on network/timeout errors (3 attempts with 1s, 2s, 4s backoff).
    Does NOT retry on Shopify API errors (invalid code, access_denied).

    Args:
        shop: Shopify store domain
        code: Authorization code from OAuth callback

    Returns:
        Access token string

    Raises:
        requests.exceptions.RequestException: On network errors after retries
        ValueError: On Shopify API errors (invalid code, etc.)
    """
    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        'client_id': SHOPIFY_API_KEY,
        'client_secret': SHOPIFY_API_SECRET,
        'code': code
    }

    response = requests.post(token_url, json=payload, timeout=10)

    if response.status_code != 200:
        error_data = response.json() if response.content else {}
        raise ValueError(f"Token exchange failed: {error_data.get('error', response.status_code)}")

    data = response.json()
    access_token = data.get('access_token')

    if not access_token:
        raise ValueError("No access token in response")

    return access_token


@oauth_bp.route('/callback', methods=['GET'])
def shopify_callback():
    """
    Handle Shopify OAuth callback.

    Query params:
        code: Authorization code (success)
        error: Error type (failure)
        state: State token for CSRF verification
        shop: Shop domain
    """
    code = request.args.get('code')
    error = request.args.get('error')
    state = request.args.get('state')
    shop = request.args.get('shop')

    # Verify state parameter (CSRF protection) with recovery fallback.
    stored_state = session.get('oauth_state')
    attempt = None
    if not state or state != stored_state:
        attempt = _resolve_pending_oauth_attempt(state, shop)
        if not attempt:
            _log_oauth_result(state, 'state_mismatch', 'State token mismatch or missing')
            return _render_oauth_error(
                'Security validation failed',
                'Please try connecting your store again.',
                shop
            )

        # Recover transiently lost session state (common across embedded/tunnel redirects).
        session['oauth_state'] = state
        session['oauth_shop'] = attempt.shop_domain
        current_app.logger.warning(
            'Recovered OAuth callback state via OAuthAttempt (user_id=%s shop=%s)',
            attempt.user_id,
            attempt.shop_domain,
        )

    # Clear state from session (single-use)
    session.pop('oauth_state', None)
    session.pop('oauth_shop', None)

    # Handle access_denied error
    if error == 'access_denied':
        _log_oauth_result(state, 'access_denied', 'User denied OAuth permissions')
        return _render_oauth_error(
            'Connection cancelled',
            'You clicked Cancel. We need these permissions to manage your products. '
            'Without them, we cannot update product images, descriptions, or prices.',
            shop,
            show_permissions=True
        )

    if error:
        _log_oauth_result(state, f'error_{error}', f'OAuth error: {error}')
        return _render_oauth_error(
            'Authorization failed',
            f'Shopify returned an error: {error}. Please try again.',
            shop
        )

    if not code:
        _log_oauth_result(state, 'no_code', 'No authorization code received')
        return _render_oauth_error(
            'Authorization incomplete',
            'No authorization code received from Shopify. Please try again.',
            shop
        )

    # Get user from session or recovered OAuth attempt.
    if not current_user.is_authenticated:
        if attempt and attempt.user:
            login_user(attempt.user, remember=False)

    if not current_user.is_authenticated:
        _log_oauth_result(state, 'not_authenticated', 'User not logged in during callback')
        return _render_oauth_error(
            'Session expired',
            'Your session has expired. Please log in and try connecting your store again.',
            shop,
            login_required=True
        )

    if attempt and current_user.id != attempt.user_id:
        _log_oauth_result(state, 'state_mismatch', 'Authenticated user does not match OAuth attempt owner')
        return _render_oauth_error(
            'Security validation failed',
            'Please restart Shopify connection from onboarding.',
            shop,
        )

    try:
        # Exchange code for access token (with retry)
        access_token = exchange_code_for_token(shop, code)

        # Create or update ShopifyStore
        store = ShopifyStore.query.filter_by(user_id=current_user.id).first()

        if not store:
            store = ShopifyStore(
                user_id=current_user.id,
                shop_domain=shop,
                shop_name=shop.split('.')[0]
            )
            db.session.add(store)
        else:
            # Update existing store (might be reconnecting)
            store.shop_domain = shop
            store.shop_name = shop.split('.')[0]
            store.is_active = True

        # Encrypt and store access token
        store.set_access_token(access_token)

        # Update user account status to ACTIVE
        if current_user.account_status == AccountStatus.PENDING_OAUTH:
            current_user.account_status = AccountStatus.ACTIVE

        # If account was INCOMPLETE (expired grace period), reactivate
        if current_user.account_status == AccountStatus.INCOMPLETE:
            current_user.account_status = AccountStatus.ACTIVE

        db.session.commit()

        # Provision physical tenant schema isolation (Postgres Schema-per-tenant)
        # This creates the tenant_store_{id} schema and its private tables.
        # This is the "Forensic Bedrock" for isolated user data.
        provision_tenant_schema(store.id)

        # Log successful OAuth
        _log_oauth_result(state, 'success', None)

        current_app.logger.info(f'OAuth successful for user {current_user.email}, shop {shop}')

        # Redirect to frontend dashboard so users return to the active Next.js app shell.
        frontend = FRONTEND_URL.rstrip('/')
        return redirect(f'{frontend}/dashboard?oauth=success')

    except requests.exceptions.RequestException as e:
        # Network/timeout error
        _log_oauth_result(state, 'network_error', str(e))
        current_app.logger.error(f'OAuth network error: {str(e)}')
        return _render_oauth_error(
            'Connection interrupted',
            'We couldn\'t connect to Shopify. This is usually temporary. Please try again.',
            shop
        )

    except ValueError as e:
        # Shopify API error (invalid code, etc.)
        _log_oauth_result(state, 'api_error', str(e))
        current_app.logger.error(f'OAuth API error: {str(e)}')
        return _render_oauth_error(
            'Authorization failed',
            'The authorization code was invalid or expired. Please try again.',
            shop
        )

    except Exception as e:
        # Unexpected error
        db.session.rollback()
        _log_oauth_result(state, 'unknown_error', str(e))
        current_app.logger.error(f'OAuth unexpected error: {str(e)}')
        return _render_oauth_error(
            'Something went wrong',
            'An unexpected error occurred. Our team has been notified. Please try again.',
            shop
        )


def _log_oauth_result(state_token: str, result: str, error_details: str = None):
    """
    Update OAuth attempt with result.

    Args:
        state_token: The state token used in the OAuth flow
        result: Result type (success, access_denied, network_error, etc.)
        error_details: Optional error details for debugging
    """
    if not state_token:
        return

    try:
        attempt = OAuthAttempt.query.filter_by(state_token=state_token).first()
        if attempt:
            attempt.result = result
            attempt.error_details = error_details
            db.session.commit()
    except Exception as e:
        current_app.logger.error(f'Failed to log OAuth result: {str(e)}')


def _render_oauth_error(title: str, message: str, shop: str = None,
                        show_permissions: bool = False, login_required: bool = False):
    """
    Render OAuth error response.

    For API requests, returns JSON. For browser, returns HTML page.
    """
    retry_url = url_for('oauth.initiate_shopify_oauth', shop=shop) if shop else None

    error_response = {
        'error': title,
        'message': message,
        'retry_url': retry_url,
        'shop': shop
    }

    if show_permissions:
        error_response['required_permissions'] = [
            {'scope': 'read_products', 'reason': 'View your product catalog'},
            {'scope': 'write_products', 'reason': 'Update product images, descriptions, and details'},
            {'scope': 'read_inventory', 'reason': 'Check stock levels'},
            {'scope': 'write_inventory', 'reason': 'Sync inventory with suppliers'},
            {'scope': 'read_locations', 'reason': 'Resolve active inventory locations for stock updates'},
            {'scope': 'write_files', 'reason': 'Upload product images'}
        ]

    if login_required:
        error_response['login_url'] = url_for('auth.login')

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify(error_response), 400
    else:
        # For browser, render error page
        # TODO: Create templates/oauth_error.html in Phase 7 (Frontend)
        return jsonify(error_response), 400


@oauth_bp.route('/status', methods=['GET'])
@login_required
def oauth_status():
    """
    Get OAuth connection status.

    Returns current store connection and any pending setup steps.
    """
    store = ShopifyStore.query.filter_by(user_id=current_user.id).first()

    return jsonify({
        'connected': store is not None and store.is_active,
        'shop_domain': store.shop_domain if store else None,
        'shop_name': store.shop_name if store else None,
        'account_status': current_user.account_status.value,
        'oauth_attempts': current_user.oauth_attempts,
        'grace_period_expires': current_user.oauth_completion_deadline.isoformat() if current_user.oauth_completion_deadline else None,
        'setup_complete': current_user.account_status == AccountStatus.ACTIVE
    }), 200


@oauth_bp.route('/disconnect', methods=['POST'])
@login_required
def disconnect_shopify():
    """
    Disconnect Shopify store.

    Removes store connection but keeps user account.
    User will need to reconnect to use store features.
    """
    store = ShopifyStore.query.filter_by(user_id=current_user.id).first()

    if not store:
        return jsonify({'error': 'No store connected'}), 400

    # Don't delete the store record, just mark inactive and clear token
    store.is_active = False
    store.access_token_encrypted = None

    # Update account status back to PENDING_OAUTH
    current_user.account_status = AccountStatus.PENDING_OAUTH

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Store disconnected. You can reconnect anytime.'
    }), 200
