"""
Tier-based rate limiting for API endpoints.

Provides Flask-Limiter configuration with tier-based rate limits
tied to user subscription levels (TIER_1, TIER_2, TIER_3).

Rate limits (from RESEARCH.md recommendations):
- TIER_1 (Starter $29/mo): 100 requests per day
- TIER_2 (Professional $99/mo): 500 requests per day
- TIER_3 (Enterprise $299/mo): 2000 requests per day
- Unauthenticated: 10 requests per hour

Storage:
- Redis backend for distributed rate limiting
- URL: redis://redis:6379/1 (Docker Compose service)

Usage:
    from src.api.core.rate_limit import create_limiter, get_user_tier_limit

    # In app factory
    limiter = create_limiter(app)

    # In route handler
    @app.route('/api/products')
    @limiter.limit(get_user_tier_limit)
    def get_products():
        return jsonify({'products': []})
"""
import os
from typing import Callable
from flask import Flask
from flask_login import current_user
from src.models import UserTier


# Tier-based rate limits (aligned with billing plans)
TIER_LIMITS = {
    UserTier.TIER_1: "100 per day",    # $29/mo Starter
    UserTier.TIER_2: "500 per day",    # $99/mo Professional
    UserTier.TIER_3: "2000 per day",   # $299/mo Enterprise
}

# Default limits for unauthenticated and fallback scenarios
DEFAULT_UNAUTHENTICATED_LIMIT = "10 per hour"
DEFAULT_LIMITS = ["200 per day", "50 per hour"]


def get_rate_limit_key() -> str:
    """
    Return user ID for authenticated users, IP for anonymous.

    This ensures:
    - Authenticated users share rate limit across sessions/devices
    - Anonymous users are limited per IP address
    - No rate limit bypass by logging out

    Returns:
        Rate limit key string (user:{id} or ip:{address})
    """
    if current_user.is_authenticated:
        return f"user:{current_user.id}"

    # Import here to avoid circular dependency
    from flask_limiter.util import get_remote_address
    return f"ip:{get_remote_address()}"


def get_user_tier_limit() -> str:
    """
    Return rate limit string based on user tier.

    This function is called by Flask-Limiter for each request
    to determine the applicable rate limit.

    Returns:
        Rate limit string (e.g., "100 per day")

    Example:
        @limiter.limit(get_user_tier_limit)
        def protected_endpoint():
            ...
    """
    if not current_user.is_authenticated:
        return DEFAULT_UNAUTHENTICATED_LIMIT

    return TIER_LIMITS.get(current_user.tier, DEFAULT_UNAUTHENTICATED_LIMIT)


def create_limiter(app: Flask):
    """
    Create and configure Flask-Limiter with Redis backend.

    Configuration:
    - Redis storage for distributed rate limiting
    - User-based key function (user ID or IP)
    - Tier-based dynamic limits
    - Default limits as fallback

    Args:
        app: Flask application instance

    Returns:
        Configured Limiter instance

    Example:
        app = Flask(__name__)
        limiter = create_limiter(app)

        @app.route('/api/resource')
        @limiter.limit(get_user_tier_limit)
        def get_resource():
            return jsonify({'data': []})
    """
    from flask_limiter import Limiter

    # Get Redis URL from environment (Docker Compose uses redis:6379)
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/1")

    limiter = Limiter(
        key_func=get_rate_limit_key,
        app=app,
        storage_uri=redis_url,
        storage_options={"socket_keepalive": True},
        default_limits=DEFAULT_LIMITS,
        # Strategy: fixed-window (simple, predictable)
        # Alternative: moving-window (more accurate but higher Redis load)
        strategy="fixed-window"
    )

    return limiter


# Export tier limits for reference in other modules
__all__ = [
    'TIER_LIMITS',
    'DEFAULT_UNAUTHENTICATED_LIMIT',
    'DEFAULT_LIMITS',
    'get_rate_limit_key',
    'get_user_tier_limit',
    'create_limiter'
]
