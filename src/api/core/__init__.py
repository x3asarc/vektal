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

# Will be populated after submodules are created
__all__ = []
