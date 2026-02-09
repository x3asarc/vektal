"""
Pagination helpers for API endpoints.

Provides cursor-based and offset-based pagination utilities following
REST best practices.

Cursor pagination:
- Use for large/changing datasets (products, jobs, vendors)
- Stable under concurrent modifications
- Opaque cursor encoding prevents tampering

Offset pagination:
- Use for small/static datasets (admin views, user lists)
- Simple page-based navigation
- Familiar for traditional pagination UIs

Usage:
    from src.api.core.pagination import (
        CursorPaginationParams,
        OffsetPaginationParams,
        encode_cursor,
        decode_cursor,
        build_cursor_response,
        build_offset_response
    )

    # Cursor pagination
    params = CursorPaginationParams(cursor=request.args.get('cursor'), limit=50)
    items = query.limit(params.limit + 1).all()
    has_next = len(items) > params.limit
    response = build_cursor_response(items[:params.limit], has_next, params.limit)

    # Offset pagination
    params = OffsetPaginationParams(page=1, limit=50)
    total = query.count()
    items = query.offset((params.page - 1) * params.limit).limit(params.limit).all()
    response = build_offset_response(items, params.page, params.limit, total)
"""
import base64
import json
from typing import Any
from pydantic import BaseModel, Field


class CursorPaginationParams(BaseModel):
    """
    Parameters for cursor-based pagination.

    Cursor pagination is recommended for:
    - Large datasets (thousands of records)
    - Frequently changing data
    - APIs where stable pagination is critical

    Attributes:
        cursor: Opaque cursor string (base64-encoded JSON)
        limit: Number of items per page (1-100, default: 50)
    """
    cursor: str | None = None
    limit: int = Field(default=50, ge=1, le=100, description="Items per page")


class OffsetPaginationParams(BaseModel):
    """
    Parameters for offset-based pagination.

    Offset pagination is recommended for:
    - Small datasets (hundreds of records)
    - Static or slowly changing data
    - Admin interfaces with traditional page numbers

    Attributes:
        page: Page number (1-indexed)
        limit: Number of items per page (1-100, default: 50)
    """
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=50, ge=1, le=100, description="Items per page")


def encode_cursor(last_id: int, last_timestamp: str) -> str:
    """
    Encode cursor for opaque pagination.

    Encodes (id, timestamp) as URL-safe base64 JSON to prevent
    cursor tampering and ensure stability under concurrent changes.

    Args:
        last_id: ID of the last item on current page
        last_timestamp: Timestamp of the last item (ISO 8601 format)

    Returns:
        URL-safe base64-encoded cursor string

    Example:
        >>> cursor = encode_cursor(123, "2026-02-09T20:00:00Z")
        >>> cursor
        'eyJpZCI6MTIzLCJ0IjoiMjAyNi0wMi0wOVQyMDowMDowMFoifQ=='
    """
    cursor_data = {
        "id": last_id,
        "t": last_timestamp
    }
    cursor_json = json.dumps(cursor_data, separators=(',', ':'))
    cursor_bytes = cursor_json.encode('utf-8')
    cursor_base64 = base64.urlsafe_b64encode(cursor_bytes).decode('utf-8')
    return cursor_base64


def decode_cursor(cursor: str) -> tuple[int, str]:
    """
    Decode cursor to extract (id, timestamp).

    Args:
        cursor: URL-safe base64-encoded cursor string

    Returns:
        Tuple of (last_id, last_timestamp)

    Raises:
        ValueError: If cursor is invalid or malformed

    Example:
        >>> cursor = encode_cursor(123, "2026-02-09T20:00:00Z")
        >>> last_id, last_timestamp = decode_cursor(cursor)
        >>> last_id
        123
        >>> last_timestamp
        '2026-02-09T20:00:00Z'
    """
    try:
        cursor_bytes = base64.urlsafe_b64decode(cursor.encode('utf-8'))
        cursor_json = cursor_bytes.decode('utf-8')
        cursor_data = json.loads(cursor_json)

        last_id = cursor_data['id']
        last_timestamp = cursor_data['t']

        return last_id, last_timestamp
    except (KeyError, json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Invalid cursor format: {str(e)}")


def build_cursor_response(
    items: list,
    has_next: bool,
    limit: int,
    cursor_field: str = "created_at"
) -> dict:
    """
    Build cursor pagination response with next_cursor if has_next.

    Response format:
    {
        "data": [...items...],
        "pagination": {
            "limit": 50,
            "has_next": true,
            "next_cursor": "eyJpZCI6MTIzLCJ0IjoiMjAyNi0wMi0wOVQyMDowMDowMFoifQ=="
        }
    }

    Args:
        items: List of items for current page
        has_next: Whether there are more items after this page
        limit: Number of items per page
        cursor_field: Field name for timestamp (default: "created_at")

    Returns:
        Dictionary with data and pagination metadata

    Example:
        >>> items = [{'id': 1, 'created_at': '2026-02-09T20:00:00Z'}]
        >>> response = build_cursor_response(items, has_next=True, limit=50)
        >>> 'next_cursor' in response['pagination']
        True
    """
    pagination = {
        "limit": limit,
        "has_next": has_next
    }

    # Add next_cursor if there are more items
    if has_next and items:
        last_item = items[-1]

        # Extract ID and timestamp from last item
        # Support both dict and object attribute access
        if isinstance(last_item, dict):
            last_id = last_item['id']
            last_timestamp = last_item[cursor_field]
        else:
            last_id = getattr(last_item, 'id')
            last_timestamp = getattr(last_item, cursor_field)

        # Convert datetime to ISO 8601 string if needed
        if hasattr(last_timestamp, 'isoformat'):
            last_timestamp = last_timestamp.isoformat()

        pagination['next_cursor'] = encode_cursor(last_id, last_timestamp)

    return {
        "data": items,
        "pagination": pagination
    }


def build_offset_response(
    items: list,
    page: int,
    limit: int,
    total: int
) -> dict:
    """
    Build offset pagination response with page info.

    Response format:
    {
        "data": [...items...],
        "pagination": {
            "page": 1,
            "limit": 50,
            "total_items": 150,
            "total_pages": 3,
            "has_next": true,
            "has_previous": false
        }
    }

    Args:
        items: List of items for current page
        page: Current page number (1-indexed)
        limit: Number of items per page
        total: Total number of items across all pages

    Returns:
        Dictionary with data and pagination metadata

    Example:
        >>> items = [{'id': 1}, {'id': 2}]
        >>> response = build_offset_response(items, page=1, limit=50, total=150)
        >>> response['pagination']['total_pages']
        3
        >>> response['pagination']['has_next']
        True
    """
    # Calculate total pages (ceiling division)
    total_pages = (total + limit - 1) // limit if total > 0 else 0

    pagination = {
        "page": page,
        "limit": limit,
        "total_items": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1
    }

    return {
        "data": items,
        "pagination": pagination
    }
