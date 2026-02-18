"""
Login, logout, and email verification endpoints.

NOTE: User REGISTRATION is handled by Stripe webhook (Plan 04).
This module only handles:
- Login for existing users
- Logout
- Email verification
- Resend verification email

Per CONTEXT.md: "Payment succeeds -> CREATE User account"
"""
from flask import Blueprint, request, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from src.models import db
from src.models.user import User, AccountStatus
from src.auth.email_verification import verify_token, generate_verification_token, generate_verification_url
from src.auth.email_sender import send_verification_email

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login endpoint.

    Request body:
    {
        "email": "user@example.com",
        "password": "password123",
        "remember_me": false  // Optional, extends session to 30 days
    }

    Returns:
        200: Login successful with user info
        400: Missing credentials
        401: Invalid credentials
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    remember_me = data.get('remember_me', False)

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    # Find user
    user = User.query.filter_by(email=email).first()

    # Check password (timing-safe comparison via bcrypt)
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Check if account is suspended
    if user.account_status == AccountStatus.SUSPENDED:
        return jsonify({
            'error': 'Account suspended',
            'message': 'Your account has been suspended. Please contact support.'
        }), 403

    # Login user (create session)
    # remember=True extends session from 7 days to 30 days
    login_user(user, remember=remember_me)

    # Make session permanent if remember_me (uses PERMANENT_SESSION_LIFETIME)
    if remember_me:
        session.permanent = True

    return jsonify({
        'success': True,
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'tier': user.tier.value,
            'account_status': user.account_status.value,
            'email_verified': user.email_verified
        },
        'warnings': _get_account_warnings(user)
    }), 200


def _get_account_warnings(user: User) -> list:
    """Get list of warnings for user's account status."""
    warnings = []

    if not user.email_verified:
        warnings.append({
            'type': 'email_verification',
            'message': 'Please verify your email address.',
            'action_url': '/auth/resend-verification'
        })

    if user.account_status == AccountStatus.PENDING_OAUTH:
        warnings.append({
            'type': 'oauth_pending',
            'message': 'Please connect your Shopify store to complete setup.',
            'action_url': '/oauth/shopify'
        })

    if user.account_status == AccountStatus.INCOMPLETE:
        warnings.append({
            'type': 'setup_incomplete',
            'message': 'Your account setup is incomplete. Please complete setup or contact support.',
            'action_url': '/account/complete-setup'
        })

    return warnings


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    User logout endpoint.

    Clears session and returns success.
    """
    logout_user()
    session.clear()  # Clear all session data

    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """
    Get current user info.

    Returns user profile and account status.
    """
    return jsonify({
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'tier': current_user.tier.value,
            'account_status': current_user.account_status.value,
            'email_verified': current_user.email_verified,
            'created_at': current_user.created_at.isoformat() if current_user.created_at else None
        },
        'warnings': _get_account_warnings(current_user)
    }), 200


@auth_bp.route('/verify-email', methods=['GET'])
def verify_email():
    """
    Email verification endpoint.

    Called when user clicks verification link in email.

    Query params:
        token: Verification token from email

    Returns:
        200: Email verified successfully
        400: Invalid or expired token
    """
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'Verification token required'}), 400

    # Verify token (1 hour expiration)
    success, result = verify_token(token)

    if not success:
        return jsonify({'error': result}), 400

    # result is the email address
    email = result
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.email_verified:
        return jsonify({
            'success': True,
            'message': 'Email already verified'
        }), 200

    # Mark email as verified
    user.email_verified = True
    user.email_verification_token = None  # Clear token

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Verification failed. Please try again.'}), 500

    return jsonify({
        'success': True,
        'message': 'Email verified successfully!',
        'next_step': 'connect_shopify' if user.account_status == AccountStatus.PENDING_OAUTH else 'dashboard'
    }), 200


@auth_bp.route('/resend-verification', methods=['POST'])
@login_required
def resend_verification():
    """
    Resend email verification link.

    Rate limited to 1 request per 5 minutes per user (TODO: implement rate limiting in Phase 4.1).
    """
    if current_user.email_verified:
        return jsonify({
            'success': True,
            'message': 'Email already verified'
        }), 200

    # Generate new token
    verification_url = generate_verification_url(current_user.email)
    token = generate_verification_token(current_user.email)
    current_user.email_verification_token = token

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to generate verification token'}), 500

    # Send verification email
    email_sent = send_verification_email(current_user.email, verification_url)

    if email_sent:
        return jsonify({
            'success': True,
            'message': 'Verification email sent. Please check your inbox.'
        }), 200
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to send email. Please try again later.',
            # Debug token only in development
            '_debug_token': token if current_app.debug else None
        }), 500


@auth_bp.route('/pending-verification', methods=['GET'])
@login_required
def pending_verification():
    """
    Page shown when email verification is required.

    Used as redirect target for @email_verified_required decorator.
    """
    return jsonify({
        'message': 'Email verification required',
        'email': current_user.email,
        'resend_url': '/auth/resend-verification'
    }), 200


@auth_bp.route('/account-status', methods=['GET'])
@login_required
def account_status():
    """
    Page showing account status and next steps.

    Used as redirect target for @active_account_required decorator.
    """
    return jsonify({
        'account_status': current_user.account_status.value,
        'email_verified': current_user.email_verified,
        'next_steps': _get_account_warnings(current_user)
    }), 200
