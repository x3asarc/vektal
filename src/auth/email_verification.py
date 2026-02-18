"""
Email verification using itsdangerous URLSafeTimedSerializer.

Tokens are:
- URL-safe (can be embedded in links)
- Signed (tamper-proof with SECRET_KEY)
- Time-limited (1 hour expiration)
- Self-contained (no database lookup needed to verify)

NOTE: Password reset tokens are deferred to Phase 4.1 per CONTEXT.md.
"""
from flask import current_app, url_for
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from typing import Tuple


def get_serializer():
    """Create serializer with app SECRET_KEY."""
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])


def generate_verification_token(email: str) -> str:
    """
    Generate email verification token.

    Args:
        email: User's email address

    Returns:
        URL-safe token string (1 hour expiration)
    """
    serializer = get_serializer()
    return serializer.dumps(email, salt='email-verification')


def verify_token(token: str, max_age: int = 3600) -> Tuple[bool, str]:
    """
    Verify email verification token.

    Args:
        token: Token from email link
        max_age: Max age in seconds (3600 = 1 hour)

    Returns:
        (success: bool, email: str or error_message: str)
    """
    serializer = get_serializer()
    try:
        email = serializer.loads(token, salt='email-verification', max_age=max_age)
        return True, email
    except SignatureExpired:
        return False, 'Token expired. Please request a new verification email.'
    except BadSignature:
        return False, 'Invalid token. Please check your email for the correct link.'


def generate_verification_url(email: str) -> str:
    """
    Generate full verification URL for email.

    Args:
        email: User's email address

    Returns:
        Full URL with token (e.g., https://app.com/auth/verify-email?token=abc123)
    """
    token = generate_verification_token(email)
    return url_for('auth.verify_email', token=token, _external=True)
