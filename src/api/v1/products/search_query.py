"""Helpers for product search filtering, sorting, and cursor contracts."""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import and_, func, or_

from src.models.product import Product

SortField = Literal["created_at", "updated_at", "title", "price", "sku", "id"]
SortDirection = Literal["asc", "desc"]

SORTABLE_FIELDS: tuple[SortField, ...] = (
    "created_at",
    "updated_at",
    "title",
    "price",
    "sku",
    "id",
)


@dataclass(frozen=True)
class SearchCursor:
    sort_by: SortField
    sort_dir: SortDirection
    sort_value: Any
    last_id: int


def _sort_expression(sort_by: SortField):
    """Return SQLAlchemy expression used for ordering and keyset comparison."""
    if sort_by == "created_at":
        return func.coalesce(
            Product.created_at,
            datetime(1970, 1, 1, tzinfo=timezone.utc),
        )
    if sort_by == "updated_at":
        return func.coalesce(
            Product.updated_at,
            datetime(1970, 1, 1, tzinfo=timezone.utc),
        )
    if sort_by == "title":
        return func.coalesce(func.lower(Product.title), "")
    if sort_by == "price":
        return func.coalesce(Product.price, Decimal("0"))
    if sort_by == "sku":
        return func.coalesce(func.lower(Product.sku), "")
    return Product.id


def apply_sort(query, *, sort_by: SortField, sort_dir: SortDirection):
    """Apply deterministic sort with id tie-breaker."""
    sort_expr = _sort_expression(sort_by)
    if sort_dir == "asc":
        return query.order_by(sort_expr.asc(), Product.id.asc())
    return query.order_by(sort_expr.desc(), Product.id.desc())


def _serialize_sort_value(sort_by: SortField, value: Any) -> str | int:
    if sort_by in {"created_at", "updated_at"}:
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)
    if sort_by == "price":
        return str(value if value is not None else Decimal("0"))
    if sort_by == "id":
        return int(value)
    return str(value if value is not None else "")


def _deserialize_sort_value(sort_by: SortField, value: Any) -> Any:
    if sort_by in {"created_at", "updated_at"}:
        if isinstance(value, str) and value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(str(value))
    if sort_by == "price":
        return Decimal(str(value))
    if sort_by == "id":
        return int(value)
    return str(value)


def encode_search_cursor(
    *,
    sort_by: SortField,
    sort_dir: SortDirection,
    sort_value: Any,
    last_id: int,
) -> str:
    payload = {
        "s": sort_by,
        "d": sort_dir,
        "v": _serialize_sort_value(sort_by, sort_value),
        "i": int(last_id),
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(blob).decode("utf-8")


def decode_search_cursor(
    cursor: str,
    *,
    expected_sort_by: SortField,
    expected_sort_dir: SortDirection,
) -> SearchCursor:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive, validated by route tests
        raise ValueError("Malformed cursor") from exc

    sort_by = payload.get("s")
    sort_dir = payload.get("d")
    if sort_by != expected_sort_by or sort_dir != expected_sort_dir:
        raise ValueError("Cursor sort contract mismatch")

    return SearchCursor(
        sort_by=sort_by,
        sort_dir=sort_dir,
        sort_value=_deserialize_sort_value(sort_by, payload.get("v")),
        last_id=int(payload.get("i")),
    )


def extract_sort_value(product: Product, *, sort_by: SortField):
    if sort_by == "created_at":
        return product.created_at or datetime(1970, 1, 1, tzinfo=timezone.utc)
    if sort_by == "updated_at":
        return product.updated_at or datetime(1970, 1, 1, tzinfo=timezone.utc)
    if sort_by == "title":
        return (product.title or "").lower()
    if sort_by == "price":
        return product.price if product.price is not None else Decimal("0")
    if sort_by == "sku":
        return (product.sku or "").lower()
    return product.id


def apply_keyset_cursor(
    query,
    *,
    sort_by: SortField,
    sort_dir: SortDirection,
    cursor: SearchCursor,
):
    sort_expr = _sort_expression(sort_by)
    if sort_dir == "asc":
        return query.filter(
            or_(
                sort_expr > cursor.sort_value,
                and_(sort_expr == cursor.sort_value, Product.id > cursor.last_id),
            )
        )
    return query.filter(
        or_(
            sort_expr < cursor.sort_value,
            and_(sort_expr == cursor.sort_value, Product.id < cursor.last_id),
        )
    )
