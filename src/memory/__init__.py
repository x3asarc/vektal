"""Multi-tier assistant memory utilities."""

from .event_log import append_event, event_log_path_for_day, iter_events
from .event_schema import EventEnvelope, EventType, create_event, validate_event
from .materializers import (
    build_long_term_index,
    build_short_term_view,
    build_working_view,
    discover_event_days,
    discover_sessions,
)
from .memory_manager import (
    LongTermMemory,
    ShortTermMemory,
    WorkingMemory,
    ensure_memory_layout,
    get_memory_paths,
)

__all__ = [
    "WorkingMemory",
    "ShortTermMemory",
    "LongTermMemory",
    "EventType",
    "EventEnvelope",
    "create_event",
    "validate_event",
    "append_event",
    "iter_events",
    "event_log_path_for_day",
    "build_working_view",
    "build_short_term_view",
    "build_long_term_index",
    "discover_event_days",
    "discover_sessions",
    "get_memory_paths",
    "ensure_memory_layout",
]
