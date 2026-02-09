"""
Shared test configuration and fixtures for API tests.
"""
import os
import pytest

# Set test environment variables before any application imports
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('FLASK_SECRET_KEY', 'test-secret-key')


class TestConfig:
    """Test configuration for Flask app."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {}  # No pool settings for SQLite
    SECRET_KEY = 'test-secret-key'
    WTF_CSRF_ENABLED = False
    ENABLE_API_VERSION_ENFORCEMENT = True
