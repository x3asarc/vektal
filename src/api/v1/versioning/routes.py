"""
User version-management route handlers.

Endpoints:
- GET  /api/v1/user/version       - Check version status
- POST /api/v1/user/migrate-to-v2 - Opt in to v2
- POST /api/v1/user/rollback-to-v1 - Rollback to v1 (if within lock window)

All endpoints require authentication.
"""
from flask import jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timezone, timedelta
from src.api.v1.versioning import versioning_bp
from src.api.v1.versioning.schemas import (
    ApiVersionStatusResponse,
    MigrateToV2Response,
    RollbackToV1Response
)
from src.api.core.errors import ProblemDetails
from src.api.core.versioning import run_user_migration
from src.models import db


@versioning_bp.route('/version', methods=['GET'])
@login_required
def get_version_status():
    """
    Get user's current API version status.

    Returns:
        200: ApiVersionStatusResponse with current version, available versions, and rollback status
        401: Authentication required

    Example:
        GET /api/v1/user/version
        Response: {
            "current_version": "v2",
            "available_versions": ["v1", "v2"],
            "lock_until": "2026-02-10T20:30:00Z",
            "rollback_available": true
        }
    """
    # Check if rollback is available
    rollback_available = False
    lock_until = None

    if current_user.api_version == 'v2' and current_user.api_version_locked_until:
        now = datetime.now(timezone.utc)
        if current_user.api_version_locked_until > now:
            rollback_available = True
            lock_until = current_user.api_version_locked_until

    response = ApiVersionStatusResponse(
        current_version=current_user.api_version,
        available_versions=['v1', 'v2'],
        lock_until=lock_until,
        rollback_available=rollback_available
    )

    return jsonify(response.model_dump()), 200


@versioning_bp.route('/migrate-to-v2', methods=['POST'])
@login_required
def migrate_to_v2():
    """
    Migrate user to API v2.

    Migration process:
    1. Check if already v2 (idempotent)
    2. Run migration service contract
    3. Update user.api_version to 'v2'
    4. Set 24h rollback lock window
    5. Commit changes

    Returns:
        200: MigrateToV2Response with migration results
        422: Migration failed (business logic error)
        401: Authentication required

    Example:
        POST /api/v1/user/migrate-to-v2
        Response: {
            "previous_version": "v1",
            "new_version": "v2",
            "migration_steps": ["Validated user eligibility", ...],
            "rollback_available_until": "2026-02-10T20:30:00Z"
        }
    """
    previous_version = current_user.api_version

    # Idempotent: already v2
    if current_user.api_version == 'v2':
        # Check if rollback window is still active
        rollback_until = None
        if current_user.api_version_locked_until:
            now = datetime.now(timezone.utc)
            if current_user.api_version_locked_until > now:
                rollback_until = current_user.api_version_locked_until

        response = MigrateToV2Response(
            previous_version='v2',
            new_version='v2',
            migration_steps=['User already on v2'],
            rollback_available_until=rollback_until
        )
        return jsonify(response.model_dump()), 200

    # Run migration service contract
    migration_result = run_user_migration(current_user.id, 'v2')

    if not migration_result['success']:
        # Migration failed - return RFC 7807 error
        return ProblemDetails.business_error(
            error_type='migration-failed',
            title='Migration to v2 Failed',
            status=422,
            detail=migration_result['error'],
            instance=request.path
        ).to_response()

    # Update user version and set rollback lock window
    current_user.api_version = 'v2'
    now = datetime.now(timezone.utc)
    current_user.api_version_locked_until = now + timedelta(hours=24)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return ProblemDetails.business_error(
            error_type='database-error',
            title='Failed to Save Migration',
            status=500,
            detail=f'Database commit failed: {str(e)}',
            instance=request.path
        ).to_response()

    response = MigrateToV2Response(
        previous_version=previous_version,
        new_version='v2',
        migration_steps=migration_result['steps'],
        rollback_available_until=current_user.api_version_locked_until
    )

    return jsonify(response.model_dump()), 200


@versioning_bp.route('/rollback-to-v1', methods=['POST'])
@login_required
def rollback_to_v1():
    """
    Rollback user to API v1 (only allowed within 24h lock window).

    Rollback requirements:
    1. User must be on v2
    2. Rollback lock window must still be active
    3. Lock is cleared after rollback

    Returns:
        200: RollbackToV1Response with rollback results
        409: Rollback not allowed (invalid state or expired window)
        401: Authentication required

    Example:
        POST /api/v1/user/rollback-to-v1
        Response: {
            "previous_version": "v2",
            "new_version": "v1"
        }
    """
    previous_version = current_user.api_version

    # Validate user is on v2
    if current_user.api_version != 'v2':
        return ProblemDetails.business_error(
            error_type='rollback-not-allowed',
            title='Rollback Not Allowed',
            status=409,
            detail=f'Rollback to v1 is only available for v2 users. You are currently on {current_user.api_version}.',
            instance=request.path,
            extensions={
                'current_version': current_user.api_version,
                'reason': 'not-on-v2'
            }
        ).to_response()

    # Validate rollback window is still active
    if not current_user.api_version_locked_until:
        return ProblemDetails.business_error(
            error_type='rollback-not-allowed',
            title='Rollback Window Expired',
            status=409,
            detail='Rollback window has expired. You cannot rollback to v1 after 24 hours.',
            instance=request.path,
            extensions={
                'current_version': current_user.api_version,
                'reason': 'no-lock-window'
            }
        ).to_response()

    now = datetime.now(timezone.utc)
    if current_user.api_version_locked_until <= now:
        return ProblemDetails.business_error(
            error_type='rollback-not-allowed',
            title='Rollback Window Expired',
            status=409,
            detail=f'Rollback window expired at {current_user.api_version_locked_until.isoformat()}. You cannot rollback to v1 after 24 hours.',
            instance=request.path,
            extensions={
                'current_version': current_user.api_version,
                'lock_expired_at': current_user.api_version_locked_until.isoformat(),
                'reason': 'window-expired'
            }
        ).to_response()

    # Perform rollback
    current_user.api_version = 'v1'
    current_user.api_version_locked_until = None

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return ProblemDetails.business_error(
            error_type='database-error',
            title='Failed to Save Rollback',
            status=500,
            detail=f'Database commit failed: {str(e)}',
            instance=request.path
        ).to_response()

    response = RollbackToV1Response(
        previous_version=previous_version,
        new_version='v1'
    )

    return jsonify(response.model_dump()), 200


__all__ = [
    'get_version_status',
    'migrate_to_v2',
    'rollback_to_v1'
]
