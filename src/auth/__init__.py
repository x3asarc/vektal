"""
Authentication module for Shopify Multi-Supplier Platform.

Provides:
- Flask-Login integration
- Flask-Session with Redis
- Tier-based access control decorators
- Email verification enforcement
- Login/logout endpoints
- Shopify OAuth integration
"""
from src.config.session_config import configure_session, configure_login_manager
from src.auth.decorators import requires_tier, email_verified_required, active_account_required
from src.auth.login import auth_bp
from src.auth.oauth import oauth_bp
from src.auth.email_verification import (
    generate_verification_token,
    verify_token,
    generate_verification_url
)
from src.auth.email_sender import (
    send_verification_email,
    send_welcome_email,
    send_oauth_reminder_email
)

__all__ = [
    # Configuration
    'configure_session',
    'configure_login_manager',

    # Decorators
    'requires_tier',
    'email_verified_required',
    'active_account_required',

    # Blueprints
    'auth_bp',
    'oauth_bp',

    # Email verification utilities
    'generate_verification_token',
    'verify_token',
    'generate_verification_url',

    # Email sending
    'send_verification_email',
    'send_welcome_email',
    'send_oauth_reminder_email'
]
