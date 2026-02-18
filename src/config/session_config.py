"""
Flask-Session configuration with Redis backend.

Sessions stored in Redis survive backend container restarts.
Redis container data persists via Docker named volume (redis_data).

Security:
- SESSION_COOKIE_SECURE: HTTPS only in production
- SESSION_COOKIE_HTTPONLY: Not accessible via JavaScript (XSS protection)
- SESSION_COOKIE_SAMESITE: 'Lax' prevents CSRF, allows OAuth redirects
"""
from flask_session import Session
from flask_login import LoginManager
from datetime import timedelta
import redis
import os
from flask import jsonify, request


def configure_session(app):
    """
    Configure Flask-Session with Redis backend.

    Args:
        app: Flask application instance
    """
    # Redis connection URL from environment
    redis_url = app.config.get('REDIS_URL', os.getenv('REDIS_URL', 'redis://redis:6379/0'))

    # Redis client (reuse connection pool)
    redis_client = redis.from_url(
        redis_url,
        decode_responses=False  # Keep bytes for session serialization
    )

    # Session storage configuration
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_REDIS'] = redis_client
    app.config['SESSION_PERMANENT'] = False  # Expires on browser close unless remember_me
    app.config['SESSION_USE_SIGNER'] = True  # Sign session cookie with SECRET_KEY
    app.config['SESSION_KEY_PREFIX'] = 'session:'  # Redis key: session:abc123

    # Security settings
    is_production = app.config.get('ENV') == 'production' or os.getenv('FLASK_ENV') == 'production'
    app_url = os.getenv('APP_URL', '')
    is_https_app_url = app_url.startswith('https://')

    # Embedded Shopify installs require SameSite=None; Secure on session cookies.
    # For local HTTP development, keep secure cookie disabled.
    cookie_secure = is_production or is_https_app_url
    app.config['SESSION_COOKIE_SECURE'] = cookie_secure
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Not accessible via JavaScript
    app.config['SESSION_COOKIE_SAMESITE'] = 'None' if cookie_secure else 'Lax'
    app.config['SESSION_COOKIE_NAME'] = 'shopify_session'  # Custom cookie name

    # Session lifetime (7 days default, 30 days with remember_me)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

    # Initialize Flask-Session
    Session(app)

    return redis_client


def configure_login_manager(app):
    """
    Configure Flask-Login with user loader.

    Args:
        app: Flask application instance

    Returns:
        LoginManager instance
    """
    login_manager = LoginManager()
    login_manager.init_app(app)

    # Redirect unauthenticated users to login page
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        """Reload user object from user ID stored in session."""
        from src.models.user import User
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        """
        Return API-safe unauthorized responses instead of redirecting to a POST-only login route.
        """
        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Authentication required',
                'message': 'Log in first via POST /api/v1/auth/login, then retry this request.',
                'login_url': '/api/v1/auth/login'
            }), 401

        return jsonify({
            'error': 'Authentication required',
            'message': 'Log in first via POST /api/v1/auth/login.'
        }), 401

    return login_manager
