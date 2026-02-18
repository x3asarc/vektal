"""Input normalization helpers for Phase 8 resolution."""
from __future__ import annotations

import re
from typing import Any

from src.resolution.contracts import NormalizedQuery


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def tokenize_title(title: str | None) -> list[str]:
    """Tokenize a title into lowercase alphanumeric terms."""
    if not title:
        return []
    return [token.lower() for token in _TOKEN_RE.findall(title)]


def normalize_input_row(
    *,
    row: dict[str, Any],
    store_id: int,
    supplier_code: str,
    supplier_verified: bool,
) -> NormalizedQuery:
    """Normalize one input row into a deterministic query contract."""
    variant_options_raw = row.get("variant_options") or []
    if isinstance(variant_options_raw, str):
        variant_options = [piece.strip() for piece in variant_options_raw.split(",") if piece.strip()]
    else:
        variant_options = [str(value).strip() for value in variant_options_raw if str(value).strip()]

    return NormalizedQuery(
        store_id=store_id,
        supplier_code=supplier_code,
        supplier_verified=supplier_verified,
        sku=_clean(row.get("sku")),
        barcode=_clean(row.get("barcode")),
        title=_clean(row.get("title")),
        variant_options=variant_options or None,
        payload=row,
    )
