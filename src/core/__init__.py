"""
Core utilities and infrastructure for Shopify Multi-Supplier Platform.

Exports:
- Graphiti client singleton and graph utilities (Phase 13.2)
"""

from src.core.graphiti_client import (
    get_graphiti_client,
    check_graph_availability,
    query_with_fallback
)

__all__ = [
    'get_graphiti_client',
    'check_graph_availability',
    'query_with_fallback'
]
