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
import re

from flask_openapi3 import OpenAPI, Info, Tag
from flask_compress import Compress
from src.api.core.errors import register_error_handlers
from src.api.core.rate_limit import create_limiter
from src.config.sentry_config import configure_sentry
from src.core.sentry_metrics import count as sentry_count
from src.core.sentry_metrics import gauge as sentry_gauge
from src.models import db


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
chat_tag = Tag(name="Chat", description="Conversational control plane and action orchestration")
ops_tag = Tag(name="Ops", description="Operational guardrails and observability endpoints")

_PATH_PARAM_RE = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")


def _to_openapi_path(rule_path: str) -> str:
    """Convert Flask route params (<int:id>) to OpenAPI params ({id})."""
    return _PATH_PARAM_RE.sub(r"{\1}", rule_path)


def _build_runtime_openapi_spec(app) -> dict:
    """
    Build OpenAPI spec from Flask URL map.

    This is used because the project registers standard Flask Blueprints,
    which are not auto-discovered by flask-openapi3 path generation.
    """
    paths: dict[str, dict] = {}

    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith("openapi.") or rule.endpoint == "static":
            continue
        if not rule.rule.startswith("/api/"):
            continue

        methods = sorted(m.lower() for m in rule.methods if m not in {"HEAD", "OPTIONS"})
        if not methods:
            continue

        openapi_path = _to_openapi_path(rule.rule)
        path_item = paths.setdefault(openapi_path, {})

        path_params = _PATH_PARAM_RE.findall(rule.rule)
        parameters = [
            {
                "name": param,
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            }
            for param in path_params
        ]

        for method in methods:
            operation = {
                "operationId": f"{rule.endpoint}_{method}",
                "responses": {"200": {"description": "Success"}},
            }
            if parameters:
                operation["parameters"] = parameters
            if openapi_path.startswith("/api/v1/"):
                operation["security"] = [{"SessionAuth": []}]
            path_item[method] = operation

    return {
        "openapi": "3.1.0",
        "info": {
            "title": info.title,
            "version": info.version,
            "description": info.description,
        },
        "paths": dict(sorted(paths.items())),
        "components": {"securitySchemes": security_schemes},
    }


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

    # Initialize Sentry error/performance monitoring if configured.
    configure_sentry()

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

    # Initialize CORS
    from flask_cors import CORS
    cors_origins = app.config.get("CORS_ORIGINS", "*")
    if isinstance(cors_origins, str) and "," in cors_origins:
        cors_origins = [origin.strip() for origin in cors_origins.split(",")]
    CORS(app, origins=cors_origins, supports_credentials=True)

    # Override OpenAPI JSON output to include all registered Flask Blueprint routes.
    if "openapi.doc_url" in app.view_functions:
        def runtime_openapi_json():
            return _build_runtime_openapi_spec(app), 200
        app.view_functions["openapi.doc_url"] = runtime_openapi_json

    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint with database connectivity check."""
        try:
            db.session.execute(db.text('SELECT 1'))
            sentry_count("api.health.check", 1, tags={"status": "ok"})
            sentry_gauge("api.health.status", 1)
            return {'status': 'ok', 'database': 'connected'}, 200
        except Exception as e:
            sentry_count("api.health.check", 1, tags={"status": "error"})
            sentry_gauge("api.health.status", 0)
            return {'status': 'error', 'database': 'disconnected', 'error': str(e)}, 500

    @app.route('/doctor', methods=['GET'])
    def doctor():
        """Comprehensive diagnostic endpoint for all critical services."""
        import redis
        from datetime import datetime, timezone

        diagnostics = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_status': 'ok',
            'services': {}
        }

        # Check PostgreSQL
        try:
            db.session.execute(db.text('SELECT version()'))
            diagnostics['services']['postgresql'] = {'status': 'ok', 'connected': True}
        except Exception as e:
            diagnostics['services']['postgresql'] = {'status': 'error', 'connected': False, 'error': str(e)}
            diagnostics['overall_status'] = 'degraded'

        # Check Redis
        try:
            redis_client = app.config.get('SESSION_REDIS')
            if redis_client:
                redis_client.ping()
                diagnostics['services']['redis'] = {'status': 'ok', 'connected': True}
            else:
                diagnostics['services']['redis'] = {'status': 'not_configured', 'connected': False}
                diagnostics['overall_status'] = 'degraded'
        except Exception as e:
            diagnostics['services']['redis'] = {'status': 'error', 'connected': False, 'error': str(e)}
            diagnostics['overall_status'] = 'degraded'

        # Check Neo4j (via health cache)
        try:
            from pathlib import Path
            import json
            health_cache_path = Path(app.root_path).parent / '.graph' / 'health-cache.json'
            if health_cache_path.exists():
                with open(health_cache_path) as f:
                    health_data = json.load(f)
                neo4j_status = health_data.get('neo4j', {})
                diagnostics['services']['neo4j'] = {
                    'status': 'ok' if neo4j_status.get('available') else 'error',
                    'connected': neo4j_status.get('available', False),
                    'last_check': neo4j_status.get('last_check_at')
                }
                if not neo4j_status.get('available'):
                    diagnostics['overall_status'] = 'degraded'
            else:
                diagnostics['services']['neo4j'] = {'status': 'unknown', 'connected': False, 'error': 'health cache not found'}
                diagnostics['overall_status'] = 'degraded'
        except Exception as e:
            diagnostics['services']['neo4j'] = {'status': 'error', 'connected': False, 'error': str(e)}
            diagnostics['overall_status'] = 'degraded'

        # Check Celery workers
        try:
            from src.celery_app import app as celery_app
            inspect = celery_app.control.inspect(timeout=2.0)
            active_workers = inspect.active()
            if active_workers:
                diagnostics['services']['celery'] = {
                    'status': 'ok',
                    'workers': list(active_workers.keys()),
                    'worker_count': len(active_workers)
                }
            else:
                diagnostics['services']['celery'] = {'status': 'warning', 'workers': [], 'worker_count': 0}
                diagnostics['overall_status'] = 'degraded'
        except Exception as e:
            diagnostics['services']['celery'] = {'status': 'error', 'error': str(e)}
            diagnostics['overall_status'] = 'degraded'

        # Check Sentry
        try:
            sentry_dsn = app.config.get('SENTRY_DSN')
            diagnostics['services']['sentry'] = {
                'status': 'ok' if sentry_dsn else 'not_configured',
                'configured': bool(sentry_dsn)
            }
        except Exception as e:
            diagnostics['services']['sentry'] = {'status': 'error', 'error': str(e)}

        # Add version and environment info
        diagnostics['version'] = app.config.get('VERSION', '1.0.0')
        diagnostics['environment'] = app.config.get('FLASK_ENV', 'production')

        status_code = 200 if diagnostics['overall_status'] == 'ok' else 503
        return diagnostics, status_code

    return app


# Export factory and tags for use in route handlers
__all__ = [
    'create_openapi_app',
    'auth_tag', 'billing_tag', 'jobs_tag',
    'products_tag', 'vendors_tag', 'oauth_tag', 'chat_tag', 'ops_tag'
]
