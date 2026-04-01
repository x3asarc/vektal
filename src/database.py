"""
Database configuration and Flask application factory.
Uses PostgreSQL with psycopg3 driver and development-friendly pool settings.
Supports physical tenant isolation via PostgreSQL schemas.
"""
import os
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from sqlalchemy import event
from src.config.session_config import configure_session, configure_login_manager
from src.models import db
from src.core.tenancy.context import get_current_store_id, get_tenant_schema_name

migrate = Migrate()


def create_app(config_override: dict = None) -> Flask:
    """
    Create Flask application with database configuration.

    Args:
        config_override: Optional config dict for testing

    Returns:
        Configured Flask application
    """
    app = Flask(__name__,
                static_folder='../web/static',
                template_folder='../web')

    # Load configuration
    configure_app(app, config_override)

    # Initialize extensions
    db.init_app(app)
    
    # Initialize Tenancy Isolation Hooks
    setup_tenancy_hooks(app)
    
    migrate.init_app(app, db, render_as_batch=True)  # batch mode for SQLite compat

    # Initialize Flask-Bcrypt for password hashing
    Bcrypt(app)

    # Initialize Flask-Session with Redis
    configure_session(app)

    # Initialize Flask-Login
    configure_login_manager(app)

    return app


def setup_tenancy_hooks(app: Flask) -> None:
    """
    Setup database hooks for physical tenant isolation.
    
    Sets the PostgreSQL search_path on every checkout to point
    to the current store's schema.
    """
    # Middleware to set the store ID context from current_user
    @app.before_request
    def set_request_tenancy():
        from flask_login import current_user
        from src.core.tenancy.context import set_current_store_id
        
        # In a real app, we might also check for a store ID in headers
        # but for v1.0, one user = one store.
        if current_user.is_authenticated:
            # We assume current_user has a shopify_store relationship
            # If not yet linked, it remains None
            store = getattr(current_user, 'shopify_store', None)
            if store:
                set_current_store_id(store.id)
            else:
                set_current_store_id(None)
        else:
            set_current_store_id(None)

    # SQLAlchemy event listener for dynamic search_path
    with app.app_context():
        @event.listens_for(db.engine, "checkout")
        def set_tenant_search_path(dbapi_connection, connection_record, connection_proxy):
            store_id = get_current_store_id()
            schema = get_tenant_schema_name(store_id)
            
            # Use raw cursor to set search_path
            # Search path: [Tenant Schema], [Public Schema]
            cursor = dbapi_connection.cursor()
            try:
                # We use a f-string here as schema name is controlled (tenant_store_{id})
                cursor.execute(f"SET search_path TO {schema}, public")
            except Exception:
                # Fallback to public if schema doesn't exist yet
                cursor.execute("SET search_path TO public")
            finally:
                cursor.close()


def configure_app(app: Flask, config_override: dict = None) -> None:
    """Configure Flask app with database settings."""
    # Secret key (from Docker secrets or env)
    from src.core.secrets import get_secret
    secret_key = get_secret('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    app.secret_key = secret_key
    app.config['SECRET_KEY'] = secret_key

    # Database URL - update postgresql:// to postgresql+psycopg:// for psycopg3
    database_url = os.getenv('DATABASE_URL', '')
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url

    # Development-friendly pool settings
    # pool_size=5, max_overflow=2 = 7 connections max per service
    # With backend + celery_worker = 14 connections (PostgreSQL default max_connections=100)
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 5,           # Keep 5 persistent connections
        'max_overflow': 2,        # Allow 2 extra during peaks
        'pool_pre_ping': True,    # Validate connections before use (handles db restarts)
        'pool_recycle': 1800,     # Recycle connections after 30 min
    }

    # Disable modification tracking (deprecated, causes overhead)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Apply overrides (for testing)
    if config_override:
        app.config.update(config_override)


def get_db():
    """Get database session for use outside request context."""
    return db
