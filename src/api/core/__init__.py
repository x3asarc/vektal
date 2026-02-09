"""
Core API utilities: errors, pagination, rate limiting.

This module exports shared infrastructure components used by all API endpoints:
- ProblemDetails: RFC 7807 error responses
- Pagination helpers: Cursor and offset pagination
- Rate limiting: Tier-based request throttling

Import examples:
    from src.api.core import ProblemDetails
    from src.api.core import encode_cursor, decode_cursor
    from src.api.core import create_limiter, get_user_tier_limit
"""

# Error handling
from src.api.core.errors import ProblemDetails, register_error_handlers

# Pagination
from src.api.core.pagination import (
    CursorPaginationParams,
    OffsetPaginationParams,
    encode_cursor,
    decode_cursor,
    build_cursor_response,
    build_offset_response
)

# Rate limiting
from src.api.core.rate_limit import (
    TIER_LIMITS,
    DEFAULT_UNAUTHENTICATED_LIMIT,
    DEFAULT_LIMITS,
    get_rate_limit_key,
    get_user_tier_limit,
    create_limiter
)

__all__ = [
    # Error handling
    'ProblemDetails',
    'register_error_handlers',
    # Pagination
    'CursorPaginationParams',
    'OffsetPaginationParams',
    'encode_cursor',
    'decode_cursor',
    'build_cursor_response',
    'build_offset_response',
    # Rate limiting
    'TIER_LIMITS',
    'DEFAULT_UNAUTHENTICATED_LIMIT',
    'DEFAULT_LIMITS',
    'get_rate_limit_key',
    'get_user_tier_limit',
    'create_limiter',
]
