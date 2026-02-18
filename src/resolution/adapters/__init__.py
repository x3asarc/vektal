"""Resolution source adapters."""

from src.resolution.adapters.shopify_adapter import search_shopify_candidates
from src.resolution.adapters.supplier_adapter import search_supplier_candidates
from src.resolution.adapters.web_adapter import search_web_candidates

__all__ = [
    "search_shopify_candidates",
    "search_supplier_candidates",
    "search_web_candidates",
]
