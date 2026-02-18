"""Typed contracts used by Phase 8 policy/lock services."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True)
class RuleContext:
    """Context for evaluating change policy."""

    supplier_code: str
    field_group: str
    now_utc: datetime
    has_consented_rules: bool
    user_id: int


@dataclass(frozen=True)
class PolicyDecision:
    """Outcome of policy evaluation for one field change."""

    status: str
    reason: str
    requires_approval: bool
    applied_rule_id: Optional[int] = None
    blocked_by_rule_id: Optional[int] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class NormalizedQuery:
    """Normalized resolver query extracted from an input row."""

    store_id: int
    supplier_code: str
    supplier_verified: bool
    sku: Optional[str] = None
    barcode: Optional[str] = None
    title: Optional[str] = None
    variant_options: Optional[list[str]] = None
    payload: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class Candidate:
    """A single candidate product match from one source."""

    source: str
    product_id: Optional[int]
    shopify_product_id: Optional[int]
    sku: Optional[str]
    barcode: Optional[str]
    title: Optional[str]
    price: Optional[float]
    variant_options: Optional[list[str]] = None
    payload: Optional[dict[str, Any]] = None
    confidence_score: Optional[float] = None
    confidence_badge: Optional[str] = None
    reason_sentence: Optional[str] = None
    reason_factors: Optional[dict[str, Any]] = None
