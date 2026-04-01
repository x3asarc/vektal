"""
Thread-safe tenancy context management.

Provides utilities to set, get, and clear the current store/tenant ID 
for the active request or background task.
"""
import contextvars
from typing import Optional

# Current active store ID context variable
_current_store_id: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "current_store_id", default=None
)

def set_current_store_id(store_id: Optional[int]) -> None:
    """Set the active store ID for the current context."""
    _current_store_id.set(store_id)

def get_current_store_id() -> Optional[int]:
    """Retrieve the active store ID for the current context."""
    return _current_store_id.get()

def clear_current_store_id() -> None:
    """Clear the active store ID context."""
    _current_store_id.set(None)

def get_tenant_schema_name(store_id: Optional[int] = None) -> str:
    """
    Generate the PostgreSQL schema name for a given store.
    
    Args:
        store_id: Optional store ID (defaults to current context)
        
    Returns:
        Schema name string (e.g., 'tenant_store_1')
    """
    sid = store_id or get_current_store_id()
    if sid is None:
        return "public"
    return f"tenant_store_{sid}"
