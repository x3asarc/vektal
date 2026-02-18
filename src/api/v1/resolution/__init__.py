"""Resolution API v1 blueprint."""
from flask import Blueprint

resolution_bp = Blueprint("resolution_v1", __name__)

# Import routes for side effects (blueprint registration decorators)
from src.api.v1.resolution import routes  # noqa: F401,E402

__all__ = ["resolution_bp"]

