"""
OpenAPI-enabled Flask application factory.

Provides Flask app with automatic API documentation generation using
Flask-OpenAPI3. Swagger UI is available at /api/docs for interactive
endpoint exploration and testing.

Features:
- Automatic OpenAPI schema generation
- Interactive Swagger UI documentation
- Response compression (gzip)
- Tier-based rate limiting
- RFC 7807 error handling
- Session-based authentication

Architecture:
- OpenAPI metadata and security schemes defined here
- Tag definitions for endpoint grouping (auth, billing, jobs, products, vendors, oauth)
- Blueprint registration delegated to src.api.__init__.register_v1_blueprints()
"""
from flask_openapi3 import OpenAPI, Info, Tag
from flask_compress import Compress
from src.api.core.errors import register_error_handlers
from src.api.core.rate_limit import create_limiter


# OpenAPI metadata
info = Info(
    title="Shopify Multi-Supplier API",
    version="1.0.0",
    description="RESTful API for multi-supplier Shopify product management with AI-powered enrichment"
)

# Security schemes (session-based authentication)
security_schemes = {
    "SessionAuth": {
        "type": "apiKey",
        "in": "cookie",
        "name": "session",
        "description": "Flask session cookie authentication (set after /api/v1/auth/login)"
    }
}

# Tag definitions for API documentation grouping
auth_tag = Tag(name="Authentication", description="User login, logout, registration, and email verification")
billing_tag = Tag(name="Billing", description="Stripe checkout and subscription management")
jobs_tag = Tag(name="Jobs", description="Scraping job management and status tracking")
products_tag = Tag(name="Products", description="Product catalog operations (CRUD, search, enrichment)")
vendors_tag = Tag(name="Vendors", description="Vendor configuration and catalog management")
oauth_tag = Tag(name="OAuth", description="Shopify OAuth integration and store connection")


def create_openapi_app(config_object=None):
    """
    Create Flask app with OpenAPI documentation support.

    This factory initializes a Flask application with:
    - OpenAPI 3.0 specification generation
    - Swagger UI at /api/docs
    - Database connection (PostgreSQL)
    - Session management (Redis)
    - Authentication (Flask-Login)
    - Email sending (Flask-Mail)
    - Rate limiting (Flask-Limiter + Redis)
    - Response compression (gzip)
    - RFC 7807 error handlers
    - All API blueprints (auth, billing, oauth, jobs, products, vendors)

    Args:
        config_object: Optional config class or path (default: src.config.Config)

    Returns:
        Configured Flask OpenAPI application

    Example:
        app = create_openapi_app()
        app.run(debug=True, host='0.0.0.0', port=5000)
    """
    app = OpenAPI(
        __name__,
        info=info,
        security_schemes=security_schemes,
        doc_ui=True,  # Enable Swagger UI
        doc_prefix="/api/docs",  # Swagger UI URL
        static_folder='../web/static',
        template_folder='../web'
    )

    # Load configuration
    if config_object:
        app.config.from_object(config_object)
    else:
        # Use database.py configure_app for consistent configuration
        from src.database import configure_app
        configure_app(app, config_override=None)

    # Initialize database
    from src.database import db
    db.init_app(app)

    # Initialize Flask-Migrate
    from flask_migrate import Migrate
    migrate = Migrate(app, db, render_as_batch=True)

    # Initialize session and login manager
    from src.config.session_config import configure_session, configure_login_manager
    configure_session(app)
    configure_login_manager(app)

    # Initialize Flask-Mail
    from src.config.email_config import configure_mail
    configure_mail(app)

    # Initialize rate limiter
    limiter = create_limiter(app)
    app.limiter = limiter  # Store for access in routes

    # Initialize compression
    compress = Compress()
    compress.init_app(app)

    # Configure compression settings
    app.config.setdefault("COMPRESS_MIMETYPES", [
        "text/html", "text/css", "text/xml",
        "application/json", "application/javascript",
        "application/problem+json"  # RFC 7807 error responses
    ])
    app.config.setdefault("COMPRESS_LEVEL", 6)  # Balance speed vs compression (1-9)
    app.config.setdefault("COMPRESS_MIN_SIZE", 500)  # Only compress responses >500 bytes

    # Configure API versioning
    app.config.setdefault("ENABLE_API_VERSION_ENFORCEMENT", True)

    # Register error handlers
    register_error_handlers(app)

    # Register API versioning hooks (after auth, before blueprints)
    from src.api.core.versioning import register_versioning_hooks
    register_versioning_hooks(app)

    # Register blueprints (auth, billing, oauth, jobs, products, vendors)
    from src.api import register_v1_blueprints
    register_v1_blueprints(app)

    return app


# Export factory and tags for use in route handlers
__all__ = [
    'create_openapi_app',
    'auth_tag', 'billing_tag', 'jobs_tag',
    'products_tag', 'vendors_tag', 'oauth_tag'
]
