"""
API v1 package for Shopify Multi-Supplier Platform.

Provides versioned REST API endpoints with OpenAPI documentation.

URL Structure:
- /api/v1/auth/*       - Authentication endpoints (login, logout, register)
- /api/v1/billing/*    - Stripe billing and subscriptions
- /api/v1/oauth/*      - Shopify OAuth integration
- /api/v1/webhooks/*   - Stripe webhook handlers
- /api/v1/products/*   - Product catalog operations
- /api/v1/jobs/*       - Job management and SSE streaming
- /api/v1/vendors/*    - Vendor configuration
- /auth/*              - Legacy auth endpoints (backward compatibility)
- /billing/*           - Legacy billing endpoints (backward compatibility)
- /oauth/*             - Legacy OAuth endpoints (backward compatibility)
- /webhooks/*          - Legacy webhook endpoints (backward compatibility)

Legacy routes will be deprecated after frontend migration to /api/v1/ routes.
"""


def register_v1_blueprints(app):
    """
    Register all v1 API blueprints with versioned URL prefixes.

    This function:
    1. Configures CORS for API routes (localhost:3000, localhost:5000)
    2. Registers existing blueprints under /api/v1/ (auth, oauth, billing, webhooks)
    3. Registers domain blueprints under /api/v1/ (products, jobs, vendors)
    4. Maintains legacy routes for backward compatibility

    Args:
        app: Flask OpenAPI application instance

    Example:
        from src.api.app import create_openapi_app
        from src.api import register_v1_blueprints

        app = create_openapi_app()
        register_v1_blueprints(app)
    """
    from flask_cors import CORS

    # Initialize CORS for API routes
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:3000",  # Next.js dev server
                "http://localhost:5000",  # Flask dev server
            ],
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    # Import existing blueprints (auth, billing, oauth)
    from src.auth import auth_bp, oauth_bp
    from src.billing import checkout_bp, webhooks_bp, billing_bp

    # Import new domain blueprints
    from src.api.v1.products import products_bp
    from src.api.v1.jobs import jobs_api_bp
    from src.api.v1.vendors import vendors_bp
    from src.api.jobs import jobs_bp  # SSE streaming
    from src.api.v1.versioning import versioning_bp

    # ===== V1 API Routes (versioned, preferred) =====
    # Register auth blueprints under /api/v1/
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(oauth_bp, url_prefix='/api/v1/oauth')

    # Register billing blueprints under /api/v1/
    app.register_blueprint(checkout_bp, url_prefix='/api/v1/billing', name='checkout_v1')
    app.register_blueprint(billing_bp, url_prefix='/api/v1/billing', name='billing_v1')
    app.register_blueprint(webhooks_bp, url_prefix='/api/v1/webhooks')

    # Register new domain blueprints under /api/v1/
    app.register_blueprint(products_bp, url_prefix='/api/v1/products')
    app.register_blueprint(jobs_api_bp, url_prefix='/api/v1/jobs')
    app.register_blueprint(vendors_bp, url_prefix='/api/v1/vendors')
    app.register_blueprint(jobs_bp, url_prefix='/api/v1/jobs')  # SSE routes
    app.register_blueprint(versioning_bp, url_prefix='/api/v1/user')

    # ===== Legacy Routes (backward compatibility) =====
    # Keep /auth and /billing working during transition
    # These can be deprecated after frontend migration to /api/v1/ routes
    app.register_blueprint(auth_bp, url_prefix='/auth', name='auth_legacy')
    app.register_blueprint(oauth_bp, url_prefix='/oauth', name='oauth_legacy')
    app.register_blueprint(checkout_bp, url_prefix='/billing', name='checkout_legacy')
    app.register_blueprint(billing_bp, url_prefix='/billing', name='billing_legacy')
    app.register_blueprint(webhooks_bp, url_prefix='/webhooks', name='webhooks_legacy')


# Export the registration function
__all__ = ['register_v1_blueprints']
