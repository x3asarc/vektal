"""Products API v1 blueprint."""
from flask import Blueprint

products_bp = Blueprint('products_v1', __name__)

# Register sub-modules (Modular Refactor)
from src.api.v1.products import core
from src.api.v1.products import enrichment
from src.api.v1.products import lineage
from src.api.v1.products import bulk

__all__ = ['products_bp']
