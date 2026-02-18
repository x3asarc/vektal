"""
Authentication and authorization decorators.

Usage:
    @app.route('/protected')
    @login_required
    def protected():
        return 'Logged in!'

    @app.route('/tier2-feature')
    @login_required
    @requires_tier(UserTier.TIER_2)
    def tier2_feature():
        return 'Tier 2 only!'

    @app.route('/verified-only')
    @login_required
    @email_verified_required
    def verified_only():
        return 'Email verified!'

IMPORTANT: Apply decorators in order:
1. @login_required (checks authentication)
2. @requires_tier or @email_verified_required (checks authorization)
"""
from functools import wraps
from flask import jsonify, redirect, url_for, flash, request
from flask_login import current_user


def requires_tier(minimum_tier):
    """
    Decorator to enforce minimum tier requirement.

    Args:
        minimum_tier: UserTier enum value (TIER_1, TIER_2, or TIER_3)

    Returns:
        403 JSON response if user's tier is below minimum
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from src.models.user import UserTier

            # Check authentication (should be handled by @login_required)
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401

            # Tier comparison (enum values: TIER_1=1, TIER_2=2, TIER_3=3)
            tier_levels = {
                UserTier.TIER_1: 1,
                UserTier.TIER_2: 2,
                UserTier.TIER_3: 3
            }

            user_level = tier_levels.get(current_user.tier, 0)
            required_level = tier_levels.get(minimum_tier, 0)

            if user_level < required_level:
                # Check if request expects JSON (API) or HTML (browser)
                if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                    return jsonify({
                        'error': 'Insufficient tier',
                        'message': f'This feature requires {minimum_tier.value}',
                        'required': minimum_tier.value,
                        'current': current_user.tier.value,
                        'upgrade_url': '/billing/upgrade'
                    }), 403
                else:
                    flash(f'This feature requires {minimum_tier.value}. Please upgrade your plan.', 'warning')
                    return redirect(url_for('billing.upgrade'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def email_verified_required(f):
    """
    Decorator to require email verification.

    Blocks access to protected features until email is verified.
    Per CONTEXT.md: Can login and browse, cannot connect Shopify or run jobs.

    Returns:
        403 JSON response or redirect if email not verified
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401

        if not current_user.email_verified:
            # Check if request expects JSON (API) or HTML (browser)
            if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                return jsonify({
                    'error': 'Email verification required',
                    'message': 'Please verify your email address to access this feature.',
                    'resend_url': '/auth/resend-verification'
                }), 403
            else:
                flash('Please verify your email address to access this feature.', 'warning')
                return redirect(url_for('auth.pending_verification'))

        return f(*args, **kwargs)
    return decorated_function


def active_account_required(f):
    """
    Decorator to require ACTIVE account status.

    Blocks users with PENDING_OAUTH, INCOMPLETE, or SUSPENDED status.
    Most restrictive - use only for features requiring fully onboarded users.

    Returns:
        403 JSON response or redirect if account not active
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from src.models.user import AccountStatus

        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401

        if current_user.account_status != AccountStatus.ACTIVE:
            status_messages = {
                AccountStatus.PENDING_OAUTH: 'Please complete Shopify store connection.',
                AccountStatus.INCOMPLETE: 'Your account setup is incomplete. Please complete setup or contact support.',
                AccountStatus.SUSPENDED: 'Your account has been suspended. Please contact support.'
            }

            message = status_messages.get(current_user.account_status, 'Account not active.')

            if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                return jsonify({
                    'error': 'Account not active',
                    'message': message,
                    'status': current_user.account_status.value
                }), 403
            else:
                flash(message, 'warning')
                return redirect(url_for('auth.account_status'))

        return f(*args, **kwargs)
    return decorated_function
