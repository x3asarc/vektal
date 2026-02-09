"""Products API v1 blueprint."""
from flask import Blueprint

products_bp = Blueprint('products_v1', __name__)

from src.api.v1.products import routes

__all__ = ['products_bp']
