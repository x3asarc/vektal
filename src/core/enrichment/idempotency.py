"""Idempotency utilities for enrichment workloads."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


def compute_enrichment_hash(
    *,
    product_payload: dict[str, Any],
    policy_version: int,
    profile_name: str,
) -> str:
    """Compute deterministic hash key for policy-aware enrichment replay."""
    canonical = json.dumps(
        {
            "product_payload": product_payload,
            "policy_version": int(policy_version),
            "profile_name": str(profile_name),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime

    @property
    def expired(self) -> bool:
        return _now() >= self.expires_at


class EnrichmentIdempotencyCache:
    """Simple in-memory cache for idempotent enrichment reuse."""

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = max(1, int(ttl_seconds))
        self._store: dict[str, CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expired:
            self._store.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any) -> None:
        created_at = _now()
        self._store[key] = CacheEntry(
            key=key,
            value=value,
            created_at=created_at,
            expires_at=created_at + timedelta(seconds=self.ttl_seconds),
        )

    def get_or_set(self, key: str, factory) -> tuple[Any, bool]:
        """Return value and reuse flag (`True` when cache hit)."""
        cached = self.get(key)
        if cached is not None:
            return cached, True
        value = factory()
        self.set(key, value)
        return value, False

