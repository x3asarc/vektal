"""Tenant field-policy resolution and threshold evaluation helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.models import AssistantFieldPolicy, ResolutionChange, db


DEFAULT_IMMUTABLE_FIELDS = {"store_currency", "admin_email", "tenant_id"}
DEFAULT_HITL_THRESHOLDS = {
    "inventory_change_absolute": 100.0,
    "price_change_percent": 15.0,
}
DEFAULT_DR_OBJECTIVES = {
    "single_tenant_rto_seconds": 120,
    "single_tenant_rpo_seconds": 300,
    "full_system_rto_seconds": 3600,
    "full_system_rpo_seconds": 21600,
}


@dataclass(frozen=True)
class FieldPolicySnapshot:
    policy_id: int | None
    store_id: int
    policy_version: int
    immutable_fields: set[str]
    inventory_change_absolute: float
    price_change_percent: float
    dr_objectives: dict[str, Any]


@dataclass(frozen=True)
class FieldPolicyDecision:
    is_immutable: bool
    requires_hitl: bool
    threshold_name: str | None
    observed_value: float | None
    threshold_value: float | None
    reason: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except Exception:
            return None
    if isinstance(value, dict):
        candidate = value.get("value")
        if candidate is not None:
            return _as_float(candidate)
    return None


def _from_model(row: AssistantFieldPolicy) -> FieldPolicySnapshot:
    immutable_raw = row.immutable_fields_json if isinstance(row.immutable_fields_json, list) else []
    immutable_fields = {str(item).strip().lower() for item in immutable_raw if str(item).strip()}

    thresholds = row.hitl_thresholds_json if isinstance(row.hitl_thresholds_json, dict) else {}
    inventory_change_absolute = float(
        thresholds.get("inventory_change_absolute", DEFAULT_HITL_THRESHOLDS["inventory_change_absolute"])
    )
    price_change_percent = float(
        thresholds.get("price_change_percent", DEFAULT_HITL_THRESHOLDS["price_change_percent"])
    )
    dr_objectives = row.dr_objectives_json if isinstance(row.dr_objectives_json, dict) else dict(DEFAULT_DR_OBJECTIVES)

    return FieldPolicySnapshot(
        policy_id=row.id,
        store_id=row.store_id,
        policy_version=row.policy_version,
        immutable_fields=immutable_fields,
        inventory_change_absolute=max(0.0, inventory_change_absolute),
        price_change_percent=max(0.0, price_change_percent),
        dr_objectives=dr_objectives,
    )


def _fallback_snapshot(*, store_id: int) -> FieldPolicySnapshot:
    return FieldPolicySnapshot(
        policy_id=None,
        store_id=store_id,
        policy_version=1,
        immutable_fields=set(DEFAULT_IMMUTABLE_FIELDS),
        inventory_change_absolute=float(DEFAULT_HITL_THRESHOLDS["inventory_change_absolute"]),
        price_change_percent=float(DEFAULT_HITL_THRESHOLDS["price_change_percent"]),
        dr_objectives=dict(DEFAULT_DR_OBJECTIVES),
    )


def ensure_default_field_policy(*, store_id: int, changed_by_id: int | None = None) -> AssistantFieldPolicy:
    """Create default policy for store if no active policy exists."""
    existing = (
        AssistantFieldPolicy.query.filter_by(store_id=store_id, is_active=True)
        .order_by(AssistantFieldPolicy.policy_version.desc(), AssistantFieldPolicy.id.desc())
        .first()
    )
    if existing is not None:
        return existing

    policy = AssistantFieldPolicy(
        store_id=store_id,
        policy_name="default",
        policy_version=1,
        is_active=True,
        effective_at=_now(),
        immutable_fields_json=sorted(DEFAULT_IMMUTABLE_FIELDS),
        hitl_thresholds_json=dict(DEFAULT_HITL_THRESHOLDS),
        dr_objectives_json=dict(DEFAULT_DR_OBJECTIVES),
        changed_by_id=changed_by_id,
    )
    db.session.add(policy)
    db.session.commit()
    return policy


def get_field_policy_snapshot(*, store_id: int, allow_fallback: bool = True) -> FieldPolicySnapshot:
    """Resolve active field policy snapshot for a store."""
    try:
        row = (
            AssistantFieldPolicy.query.filter(
                AssistantFieldPolicy.store_id == store_id,
                AssistantFieldPolicy.is_active.is_(True),
                AssistantFieldPolicy.effective_at <= _now(),
            )
            .order_by(AssistantFieldPolicy.policy_version.desc(), AssistantFieldPolicy.effective_at.desc())
            .first()
        )
    except Exception:
        if allow_fallback:
            return _fallback_snapshot(store_id=store_id)
        raise

    if row is None:
        if not allow_fallback:
            raise LookupError(f"No active field policy found for store_id={store_id}.")
        return _fallback_snapshot(store_id=store_id)
    return _from_model(row)


def evaluate_change_policy(*, change: ResolutionChange, snapshot: FieldPolicySnapshot) -> FieldPolicyDecision:
    """Evaluate immutable and HITL-threshold policy for one field-level change."""
    field_name = (change.field_name or "").strip().lower()
    if field_name in snapshot.immutable_fields:
        return FieldPolicyDecision(
            is_immutable=True,
            requires_hitl=True,
            threshold_name=None,
            observed_value=None,
            threshold_value=None,
            reason="immutable_field_blocked",
        )

    before_value = _as_float(change.before_value)
    after_value = _as_float(change.after_value)
    if before_value is None or after_value is None:
        return FieldPolicyDecision(
            is_immutable=False,
            requires_hitl=False,
            threshold_name=None,
            observed_value=None,
            threshold_value=None,
            reason="non_numeric_or_not_thresholded_field",
        )

    if "inventory" in field_name or field_name.endswith("quantity"):
        delta = abs(after_value - before_value)
        if delta > snapshot.inventory_change_absolute:
            return FieldPolicyDecision(
                is_immutable=False,
                requires_hitl=True,
                threshold_name="inventory_change_absolute",
                observed_value=delta,
                threshold_value=snapshot.inventory_change_absolute,
                reason="inventory_threshold_breach",
            )
        return FieldPolicyDecision(
            is_immutable=False,
            requires_hitl=False,
            threshold_name="inventory_change_absolute",
            observed_value=delta,
            threshold_value=snapshot.inventory_change_absolute,
            reason="inventory_threshold_ok",
        )

    if "price" in field_name and before_value != 0:
        delta_percent = abs((after_value - before_value) / before_value) * 100.0
        if delta_percent > snapshot.price_change_percent:
            return FieldPolicyDecision(
                is_immutable=False,
                requires_hitl=True,
                threshold_name="price_change_percent",
                observed_value=delta_percent,
                threshold_value=snapshot.price_change_percent,
                reason="price_threshold_breach",
            )
        return FieldPolicyDecision(
            is_immutable=False,
            requires_hitl=False,
            threshold_name="price_change_percent",
            observed_value=delta_percent,
            threshold_value=snapshot.price_change_percent,
            reason="price_threshold_ok",
        )

    return FieldPolicyDecision(
        is_immutable=False,
        requires_hitl=False,
        threshold_name=None,
        observed_value=None,
        threshold_value=None,
        reason="threshold_not_applicable",
    )

