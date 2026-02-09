"""Vendors API v1 blueprint."""
from flask import Blueprint

vendors_bp = Blueprint('vendors_v1', __name__)

from src.api.v1.vendors import routes

__all__ = ['vendors_bp']
