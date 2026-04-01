"""Chat API v1 blueprint."""
from flask import Blueprint

chat_bp = Blueprint("chat_v1", __name__)

# Import routes for side effects (blueprint route registration)
from src.api.v1.chat import routes  # noqa: F401,E402
from src.api.v1.chat import agent   # noqa: F401,E402

__all__ = ["chat_bp"]
