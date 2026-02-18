"""
Shared test configuration and fixtures for API tests.
"""
import os
from urllib.parse import quote_plus, urlsplit, urlunsplit

import pytest
from dotenv import load_dotenv


load_dotenv(dotenv_path='.env')


def _resolve_test_database_url() -> str:
    """
    Resolve a PostgreSQL URL reachable from local test runner.

    Priority:
    1) TEST_DATABASE_URL
    2) DATABASE_URL (host normalized from docker service name to localhost)
    3) Build from DB_* environment variables
    """
    raw_url = os.getenv('TEST_DATABASE_URL') or os.getenv('DATABASE_URL')

    if raw_url:
        if raw_url.startswith('postgresql://'):
            raw_url = raw_url.replace('postgresql://', 'postgresql+psycopg://', 1)

        parsed = urlsplit(raw_url)
        host = parsed.hostname or 'localhost'
        if host == 'db':
            host = 'localhost'

        auth = ''
        if parsed.username:
            auth = parsed.username
            if parsed.password:
                auth += f":{parsed.password}"
            auth += '@'

        hostport = f"{host}:{parsed.port}" if parsed.port else host
        netloc = f"{auth}{hostport}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))

    db_user = os.getenv('DB_USER', 'admin')
    db_password = quote_plus(os.getenv('DB_PASSWORD', ''))
    db_name = os.getenv('DB_NAME', 'shopify_platform')
    db_port = os.getenv('POSTGRES_PORT', '5432')
    return f'postgresql+psycopg://{db_user}:{db_password}@localhost:{db_port}/{db_name}'


def _resolve_redis_url() -> str:
    """Normalize Redis URL for local test runner."""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    return redis_url.replace('redis://redis:', 'redis://localhost:')


# Set test environment variables before any application imports
TEST_DATABASE_URL = _resolve_test_database_url()
# Force normalized local URLs for host-run test process.
os.environ['DATABASE_URL'] = TEST_DATABASE_URL
os.environ['REDIS_URL'] = _resolve_redis_url()
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('FLASK_SECRET_KEY', 'test-secret-key')


class TestConfig:
    """Test configuration for Flask app."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = TEST_DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }
    SECRET_KEY = 'test-secret-key'
    WTF_CSRF_ENABLED = False
    ENABLE_API_VERSION_ENFORCEMENT = True
    RATELIMIT_ENABLED = False
