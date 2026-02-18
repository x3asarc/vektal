"""
API versioning enforcement and user migration infrastructure.

This module provides:
- Version extraction from API paths (/api/v1/... vs /api/v2/...)
- Per-user version enforcement middleware
- Migration service contract for transitioning users between API versions
- Response headers for version awareness

Architecture:
- Hooks registered via before_request/after_request in app factory
- Mismatch handling returns RFC 7807 409 with corrective metadata
- Feature flag gate: ENABLE_API_VERSION_ENFORCEMENT (default True)
- Migration contract stubbed for Phase 5, to be implemented in v2 phase

Example enforcement flow:
1. User with api_version='v1' calls /api/v2/products
2. before_request hook detects mismatch
3. Returns 409 with suggested_path='/api/v1/products'
"""
from flask import request, g, current_app
from flask_login import current_user
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any


def extract_requested_version(path: str) -> Optional[str]:
    """
    Extract API version from path.

    Args:
        path: Request path (e.g., '/api/v1/products', '/api/v2/jobs')

    Returns:
        'v1', 'v2', or None if not a versioned API path

    Examples:
        >>> extract_requested_version('/api/v1/products')
        'v1'
        >>> extract_requested_version('/api/v2/jobs')
        'v2'
        >>> extract_requested_version('/api/status')
        None
        >>> extract_requested_version('/auth/login')
        None
    """
    match = re.match(r'^/api/v(\d+)/', path)
    if match:
        return f'v{match.group(1)}'
    return None


def is_versioned_api_path(path: str) -> bool:
    """
    Check if path is a versioned API endpoint.

    Args:
        path: Request path

    Returns:
        True for /api/v1/* or /api/v2/* patterns, False otherwise

    Examples:
        >>> is_versioned_api_path('/api/v1/products')
        True
        >>> is_versioned_api_path('/api/status')
        False
        >>> is_versioned_api_path('/auth/login')
        False
    """
    return extract_requested_version(path) is not None


def register_versioning_hooks(app):
    """
    Register before_request/after_request hooks for user API version enforcement.

    Enforcement logic:
    - Apply only to authenticated requests and /api/ paths
    - Skip non-versioned legacy endpoints (/api/status, etc.)
    - If requested version != current_user.api_version, return RFC 7807 409
    - Include correction metadata in response extensions
    - Respect feature flag ENABLE_API_VERSION_ENFORCEMENT (default True)

    Response headers added:
    - X-API-Version: User's effective API version
    - X-API-Version-Lock-Until: Rollback lock expiry (if present)

    Args:
        app: Flask application instance
    """
    from src.api.core.errors import ProblemDetails

    @app.before_request
    def enforce_user_api_version():
        """
        Check if authenticated user is accessing correct API version.

        Returns 409 if version mismatch, otherwise allows request to proceed.
        """
        # Feature flag gate
        if not app.config.get('ENABLE_API_VERSION_ENFORCEMENT', True):
            return None

        # Only enforce on authenticated requests
        if not current_user.is_authenticated:
            return None

        # Only enforce on API paths
        if not request.path.startswith('/api/'):
            return None

        # Extract requested version
        requested_version = extract_requested_version(request.path)

        # Skip non-versioned API paths (e.g., /api/status, /api/docs)
        if requested_version is None:
            return None

        # Always allow user version-management control plane.
        # These endpoints are intentionally hosted under /api/v1/user/*
        # for migration/rollback regardless of current user version.
        if request.path.startswith('/api/v1/user/'):
            return None

        # Check for version mismatch
        user_version = current_user.api_version
        if requested_version != user_version:
            # Build suggested path by replacing version
            suggested_path = request.path.replace(f'/api/{requested_version}/', f'/api/{user_version}/', 1)

            # Return RFC 7807 409 with corrective metadata
            return ProblemDetails.business_error(
                error_type='version-mismatch',
                title='API Version Mismatch',
                status=409,
                detail=f'You are using API {user_version} but requested {requested_version}. Please use the correct version endpoint.',
                instance=request.path,
                user_version=user_version,
                requested_version=requested_version,
                suggested_path=suggested_path
            )

        return None

    @app.after_request
    def add_version_headers(response):
        """
        Add API version headers to authenticated API responses.

        Headers added:
        - X-API-Version: User's effective API version
        - X-API-Version-Lock-Until: Rollback lock expiry (ISO 8601, if present)
        """
        # Only add headers for authenticated API requests
        if not current_user.is_authenticated:
            return response

        if not request.path.startswith('/api/'):
            return response

        # Add effective API version header
        response.headers['X-API-Version'] = current_user.api_version

        # Add lock-until header if rollback window is active
        if current_user.api_version_locked_until:
            # Format as ISO 8601 with timezone
            lock_until = current_user.api_version_locked_until
            if lock_until.tzinfo is None:
                lock_until = lock_until.replace(tzinfo=timezone.utc)
            lock_until_iso = lock_until.isoformat()
            response.headers['X-API-Version-Lock-Until'] = lock_until_iso

        return response


def run_user_migration(user_id: int, target_version: str) -> Dict[str, Any]:
    """
    Execute user-scoped migration and return results.

    This is the migration service contract. Phase 5 provides a deterministic
    placeholder that returns success for target_version='v2'. Future phases
    will implement actual data-shape transformations.

    Migration contract:
    1. Validate user exists and is eligible for migration
    2. Execute data transformations (if any)
    3. Return success/failure with detailed steps

    Args:
        user_id: User ID to migrate
        target_version: Target API version ('v2', future: 'v3', etc.)

    Returns:
        Dict with keys:
            - success (bool): True if migration succeeded
            - steps (list[str]): List of migration steps executed
            - error (str | None): Error message if migration failed

    Examples:
        >>> result = run_user_migration(123, 'v2')
        >>> result['success']
        True
        >>> result['steps']
        ['Validated user eligibility', 'Prepared for v2 migration', ...]

    TODO: Phase v2 implementation:
        - Add data-shape transformations (schema changes, data rewrites)
        - Add rollback capability (store pre-migration snapshot)
        - Add validation checks (ensure data integrity post-migration)
        - Add idempotency (allow re-running on partial failures)
    """
    from src.models import db
    from src.models.user import User

    # Validate user exists
    user = db.session.get(User, user_id)
    if not user:
        return {
            'success': False,
            'steps': [],
            'error': f'User {user_id} not found'
        }

    # Phase 5 placeholder: deterministic success for v2 migration
    if target_version == 'v2':
        steps = [
            'Validated user eligibility',
            'Prepared for v2 migration',
            'Migration ready (no data transformations required in Phase 5)',
            'User can safely use v2 API endpoints'
        ]
        return {
            'success': True,
            'steps': steps,
            'error': None
        }

    # Unsupported version
    return {
        'success': False,
        'steps': [],
        'error': f'Migration to {target_version} not supported'
    }


__all__ = [
    'extract_requested_version',
    'is_versioned_api_path',
    'register_versioning_hooks',
    'run_user_migration'
]
