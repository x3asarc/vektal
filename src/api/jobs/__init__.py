"""
Jobs API v1 blueprint.

Provides endpoints for job management, status tracking, and real-time progress updates.
"""
from flask import Blueprint

jobs_bp = Blueprint('jobs_v1', __name__)

# Import routes to register them
from src.api.jobs import events  # SSE streaming routes

__all__ = ['jobs_bp']
