"""Jobs API v1 blueprint."""
from flask import Blueprint

jobs_api_bp = Blueprint('jobs_api_v1', __name__)

from src.api.v1.jobs import routes

__all__ = ['jobs_api_bp']
