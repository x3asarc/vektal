"""
User version-management blueprint for API v1.

Provides endpoints for users to:
- Check their current API version status
- Migrate to v2 (opt-in)
- Rollback to v1 (within 24h lock window)

Endpoints:
- GET  /api/v1/user/version       - Check version status
- POST /api/v1/user/migrate-to-v2 - Opt in to v2
- POST /api/v1/user/rollback-to-v1 - Rollback to v1 (if within lock window)
"""
from flask import Blueprint

# Create versioning blueprint
versioning_bp = Blueprint('versioning_v1', __name__)

# Import routes to register them with blueprint
from src.api.v1.versioning import routes

__all__ = ['versioning_bp']
