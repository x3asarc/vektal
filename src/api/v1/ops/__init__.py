"""Ops API v1 blueprint."""
from flask import Blueprint

ops_bp = Blueprint("ops_v1", __name__)

from src.api.v1.ops import routes  # noqa: F401,E402

__all__ = ["ops_bp"]

