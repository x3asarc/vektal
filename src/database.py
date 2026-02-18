"""
Database configuration and Flask application factory.
Uses PostgreSQL with psycopg3 driver and development-friendly pool settings.
"""
import os
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from src.config.session_config import configure_session, configure_login_manager
from src.models import db

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
    migrate.init_app(app, db, render_as_batch=True)  # batch mode for SQLite compat

    # Initialize Flask-Bcrypt for password hashing
    Bcrypt(app)

    # Initialize Flask-Session with Redis
    configure_session(app)

    # Initialize Flask-Login
    configure_login_manager(app)

    return app


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
