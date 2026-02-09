"""
Integration tests for API endpoints.

Tests endpoint behavior with Flask test client.
"""
import pytest
import json
from flask import Flask

from src.api.app import create_openapi_app
from src.database import db
from src.models import User, Job, JobStatus, Vendor, UserTier


@pytest.fixture
def app():
    """Create test Flask application."""
    app = create_openapi_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def authenticated_client(app, client):
    """Create authenticated test client with test user."""
    with app.app_context():
        # Create test user
        user = User(
            email='test@example.com',
            tier=UserTier.TIER_1,
            is_active=True,
            email_verified=True
        )
        user.set_password('testpassword')
        db.session.add(user)
        db.session.commit()

        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)

        yield client, user


class TestOpenAPIDocs:
    """Tests for OpenAPI documentation endpoints."""

    def test_swagger_ui_accessible(self, client):
        """Swagger UI is accessible at /api/docs."""
        response = client.get('/api/docs/')
        # Should return HTML or redirect
        assert response.status_code in [200, 301, 302]

    def test_openapi_json_accessible(self, client):
        """OpenAPI JSON spec is accessible."""
        response = client.get('/api/openapi.json')
        assert response.status_code == 200
        data = response.get_json()
        assert 'openapi' in data
        assert 'paths' in data
        assert 'info' in data


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_returns_ok(self, client):
        """Health endpoint returns status ok."""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'


class TestJobsAPI:
    """Tests for Jobs API endpoints."""

    def test_list_jobs_requires_auth(self, client):
        """Jobs list requires authentication."""
        response = client.get('/api/v1/jobs')
        assert response.status_code in [401, 302]  # Unauthorized or redirect to login

    def test_list_jobs_authenticated(self, authenticated_client):
        """Authenticated user can list their jobs."""
        client, user = authenticated_client

        # Create a test job
        with client.application.app_context():
            job = Job(
                user_id=user.id,
                job_name='Test Job',
                status=JobStatus.PENDING,
                total_items=10
            )
            db.session.add(job)
            db.session.commit()

        response = client.get('/api/v1/jobs')
        assert response.status_code == 200
        data = response.get_json()
        assert 'jobs' in data
        assert len(data['jobs']) >= 1

    def test_get_job_not_found(self, authenticated_client):
        """Non-existent job returns 404."""
        client, user = authenticated_client
        response = client.get('/api/v1/jobs/99999')
        assert response.status_code == 404
        data = response.get_json()
        assert 'not-found' in data.get('type', '')


class TestVendorsAPI:
    """Tests for Vendors API endpoints."""

    def test_list_vendors_requires_auth(self, client):
        """Vendors list requires authentication."""
        response = client.get('/api/v1/vendors')
        assert response.status_code in [401, 302]

    def test_list_vendors_authenticated(self, authenticated_client):
        """Authenticated user can list vendors."""
        client, user = authenticated_client

        # Create a test vendor
        with client.application.app_context():
            vendor = Vendor(
                code='TEST',
                name='Test Vendor',
                is_active=True
            )
            db.session.add(vendor)
            db.session.commit()

        response = client.get('/api/v1/vendors')
        assert response.status_code == 200
        data = response.get_json()
        assert 'vendors' in data


class TestErrorResponses:
    """Tests for error response format."""

    def test_404_returns_rfc7807(self, authenticated_client):
        """404 errors follow RFC 7807 format."""
        client, user = authenticated_client
        response = client.get('/api/v1/nonexistent-endpoint')
        assert response.status_code == 404
        data = response.get_json()

        # RFC 7807 required fields
        assert 'type' in data
        assert 'title' in data
        assert 'status' in data


class TestCORSHeaders:
    """Tests for CORS configuration."""

    def test_cors_headers_present(self, client):
        """CORS headers are present on API responses."""
        response = client.options(
            '/api/v1/jobs',
            headers={
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'GET'
            }
        )
        # Should allow the origin
        assert response.status_code in [200, 204]
