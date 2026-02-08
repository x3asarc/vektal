"""
Chat Routing Infrastructure (Backend Only)

This module provides intent classification and routing for chat messages.
It is consumed by:
- Phase 5: REST API endpoints (POST /api/chat/message)
- Phase 10: ChatGPT-style frontend UI

No frontend components here - this is pure Python backend logic.
"""
from .router import ChatRouter, Intent, RouteResult, IntentType

# Handlers imported on demand to avoid circular imports
__all__ = [
    "ChatRouter",
    "Intent",
    "RouteResult",
    "IntentType"
]

def __getattr__(name):
    """Lazy import handlers."""
    if name == "ProductHandler":
        from .handlers.product import ProductHandler
        return ProductHandler
    elif name == "VendorHandler":
        from .handlers.vendor import VendorHandler
        return VendorHandler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
