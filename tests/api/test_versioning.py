"""
Tests for API versioning infrastructure.

Tests cover:
- User model defaults (api_version='v1', lock=None)
- Middleware enforcement (version mismatch → 409)
- Migration endpoint (v1 → v2 with lock window)
- Rollback endpoint (v2 → v1 within window, reject after expiry)
- Response headers (X-API-Version, X-API-Version-Lock-Until)

Fixtures:
- app: Flask test app with versioning enabled
- client: Flask test client
- authenticated_user: Logged-in v1 user
- v2_user_with_lock: Logged-in v2 user with active rollback window
- v2_user_expired_lock: Logged-in v2 user with expired rollback window
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from src.models import db
from src.models.user import User, UserTier, AccountStatus
from src.api.app import create_openapi_app


class TestConfig:
    """Test configuration for Flask app."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {}  # No pool settings for SQLite
    SECRET_KEY = 'test-secret-key'
    WTF_CSRF_ENABLED = False
    ENABLE_API_VERSION_ENFORCEMENT = True


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_openapi_app(config_object=TestConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def authenticated_user(app, client):
    """
    Create and authenticate a v1 user.

    Returns:
        User: Authenticated user with api_version='v1'
    """
    with app.app_context():
        user = User(
            email='testuser@example.com',
            tier=UserTier.TIER_1,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version='v1',
            api_version_locked_until=None
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Log in
    client.post('/api/v1/auth/login', json={
        'email': 'testuser@example.com',
        'password': 'password123'
    })

    with app.app_context():
        return db.session.get(User, user_id)


@pytest.fixture
def v2_user_with_lock(app, client):
    """
    Create and authenticate a v2 user with active rollback window.

    Returns:
        User: Authenticated user with api_version='v2' and lock_until in future
    """
    with app.app_context():
        now = datetime.now(timezone.utc)
        user = User(
            email='v2user@example.com',
            tier=UserTier.TIER_2,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version='v2',
            api_version_locked_until=now + timedelta(hours=12)
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Log in
    client.post('/api/v1/auth/login', json={
        'email': 'v2user@example.com',
        'password': 'password123'
    })

    with app.app_context():
        return db.session.get(User, user_id)


@pytest.fixture
def v2_user_expired_lock(app, client):
    """
    Create and authenticate a v2 user with expired rollback window.

    Returns:
        User: Authenticated user with api_version='v2' and lock_until in past
    """
    with app.app_context():
        now = datetime.now(timezone.utc)
        user = User(
            email='v2expired@example.com',
            tier=UserTier.TIER_3,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version='v2',
            api_version_locked_until=now - timedelta(hours=1)
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Log in
    client.post('/api/v1/auth/login', json={
        'email': 'v2expired@example.com',
        'password': 'password123'
    })

    with app.app_context():
        return db.session.get(User, user_id)


# ===== Model Defaults Tests =====

def test_new_user_defaults_to_v1(app):
    """New users default to api_version='v1' with no lock."""
    with app.app_context():
        user = User(
            email='newuser@example.com',
            tier=UserTier.TIER_1,
            account_status=AccountStatus.PENDING_OAUTH,
            email_verified=False
        )
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

        assert user.api_version == 'v1'
        assert user.api_version_locked_until is None


# ===== Middleware Enforcement Tests =====

def test_v1_user_accessing_v2_endpoint_gets_409(client, authenticated_user):
    """v1 user accessing /api/v2/... gets 409 with suggested_path."""
    response = client.get('/api/v2/products')

    assert response.status_code == 409
    data = response.get_json()
    assert data['type'] == 'version-mismatch'
    assert data['user_version'] == 'v1'
    assert data['requested_version'] == 'v2'
    assert data['suggested_path'] == '/api/v1/products'


def test_v2_user_accessing_v1_endpoint_gets_409(client, v2_user_with_lock):
    """v2 user accessing /api/v1/... gets 409 with suggested_path."""
    response = client.get('/api/v1/products')

    assert response.status_code == 409
    data = response.get_json()
    assert data['type'] == 'version-mismatch'
    assert data['user_version'] == 'v2'
    assert data['requested_version'] == 'v1'
    assert data['suggested_path'] == '/api/v2/products'


def test_v1_user_accessing_v1_endpoint_succeeds(client, authenticated_user):
    """v1 user accessing /api/v1/... succeeds (no version mismatch)."""
    # /api/v1/user/version is a versioning endpoint, should succeed
    response = client.get('/api/v1/user/version')

    # Should not be 409 (version mismatch)
    assert response.status_code != 409


def test_unauthenticated_request_skips_enforcement(client):
    """Unauthenticated requests bypass version enforcement."""
    # No login, so enforcement should be skipped
    # This will likely return 401 or 302, but NOT 409
    response = client.get('/api/v2/products')

    # Should not be 409 (version enforcement skipped for unauthenticated)
    assert response.status_code != 409


# ===== Migration Endpoint Tests =====

def test_migrate_v1_to_v2_succeeds(app, client, authenticated_user):
    """POST /api/v1/user/migrate-to-v2 updates user to v2 with 24h lock."""
    response = client.post('/api/v1/user/migrate-to-v2')

    assert response.status_code == 200
    data = response.get_json()
    assert data['previous_version'] == 'v1'
    assert data['new_version'] == 'v2'
    assert 'migration_steps' in data
    assert data['rollback_available_until'] is not None

    # Verify database update
    with app.app_context():
        user = db.session.get(User, authenticated_user.id)
        assert user.api_version == 'v2'
        assert user.api_version_locked_until is not None
        assert user.api_version_locked_until > datetime.now(timezone.utc)


def test_migrate_to_v2_idempotent(app, client, v2_user_with_lock):
    """Migrating already-v2 user returns success (idempotent)."""
    response = client.post('/api/v1/user/migrate-to-v2')

    assert response.status_code == 200
    data = response.get_json()
    assert data['previous_version'] == 'v2'
    assert data['new_version'] == 'v2'
    assert 'User already on v2' in data['migration_steps']


# ===== Rollback Endpoint Tests =====

def test_rollback_within_window_succeeds(app, client, v2_user_with_lock):
    """POST /api/v1/user/rollback-to-v1 succeeds within lock window."""
    response = client.post('/api/v1/user/rollback-to-v1')

    assert response.status_code == 200
    data = response.get_json()
    assert data['previous_version'] == 'v2'
    assert data['new_version'] == 'v1'

    # Verify database update
    with app.app_context():
        user = db.session.get(User, v2_user_with_lock.id)
        assert user.api_version == 'v1'
        assert user.api_version_locked_until is None


def test_rollback_after_expiry_rejected(client, v2_user_expired_lock):
    """POST /api/v1/user/rollback-to-v1 rejected after lock expiry."""
    response = client.post('/api/v1/user/rollback-to-v1')

    assert response.status_code == 409
    data = response.get_json()
    assert data['type'] == 'rollback-not-allowed'
    assert 'expired' in data['title'].lower()


def test_rollback_v1_user_rejected(client, authenticated_user):
    """v1 user cannot rollback (only v2 users can rollback)."""
    response = client.post('/api/v1/user/rollback-to-v1')

    assert response.status_code == 409
    data = response.get_json()
    assert data['type'] == 'rollback-not-allowed'
    assert data['reason'] == 'not-on-v2'


# ===== Version Status Endpoint Tests =====

def test_version_status_v1_user(client, authenticated_user):
    """GET /api/v1/user/version for v1 user."""
    response = client.get('/api/v1/user/version')

    assert response.status_code == 200
    data = response.get_json()
    assert data['current_version'] == 'v1'
    assert 'v1' in data['available_versions']
    assert 'v2' in data['available_versions']
    assert data['rollback_available'] is False
    assert data['lock_until'] is None


def test_version_status_v2_user_with_lock(client, v2_user_with_lock):
    """GET /api/v1/user/version for v2 user with active lock."""
    response = client.get('/api/v1/user/version')

    assert response.status_code == 200
    data = response.get_json()
    assert data['current_version'] == 'v2'
    assert data['rollback_available'] is True
    assert data['lock_until'] is not None


def test_version_status_v2_user_expired_lock(client, v2_user_expired_lock):
    """GET /api/v1/user/version for v2 user with expired lock."""
    response = client.get('/api/v1/user/version')

    assert response.status_code == 200
    data = response.get_json()
    assert data['current_version'] == 'v2'
    assert data['rollback_available'] is False


# ===== Response Headers Tests =====

def test_api_version_header_present(client, authenticated_user):
    """X-API-Version header present in authenticated API responses."""
    response = client.get('/api/v1/user/version')

    assert response.status_code == 200
    assert 'X-API-Version' in response.headers
    assert response.headers['X-API-Version'] == 'v1'


def test_lock_until_header_present_when_locked(client, v2_user_with_lock):
    """X-API-Version-Lock-Until header present when lock is active."""
    response = client.get('/api/v1/user/version')

    assert response.status_code == 200
    assert 'X-API-Version' in response.headers
    assert response.headers['X-API-Version'] == 'v2'
    assert 'X-API-Version-Lock-Until' in response.headers


def test_lock_until_header_absent_when_no_lock(client, authenticated_user):
    """X-API-Version-Lock-Until header absent when no lock."""
    response = client.get('/api/v1/user/version')

    assert response.status_code == 200
    assert 'X-API-Version-Lock-Until' not in response.headers
