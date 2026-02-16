"""Capability-first audit for enrichment dry-run planning."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func

from src.core.enrichment.contracts import (
    FIELD_GROUP_BY_FIELD,
    PROTECTED_COLUMNS_DEFAULT,
    SUPPORTED_MUTATION_FIELDS,
    CapabilityAuditResult,
    CapabilityDecision,
)
from src.models import AssistantFieldPolicy, VendorFieldMapping


def _resolve_active_field_policy(store_id: int) -> AssistantFieldPolicy | None:
    return (
        AssistantFieldPolicy.query.filter(
            AssistantFieldPolicy.store_id == store_id,
            AssistantFieldPolicy.is_active.is_(True),
        )
        .order_by(
            AssistantFieldPolicy.policy_version.desc(),
            AssistantFieldPolicy.effective_at.desc(),
            AssistantFieldPolicy.id.desc(),
        )
        .first()
    )


def _resolve_mapping_by_group(
    *,
    store_id: int,
    vendor_code: str,
    requested_mapping_version: int | None,
) -> dict[str, VendorFieldMapping]:
    mappings: dict[str, VendorFieldMapping] = {}
    groups = sorted(set(FIELD_GROUP_BY_FIELD.values()))
    for group in groups:
        query = VendorFieldMapping.query.filter(
            VendorFieldMapping.store_id == store_id,
            func.lower(VendorFieldMapping.vendor_code) == vendor_code.lower(),
            VendorFieldMapping.field_group == group,
            VendorFieldMapping.is_active.is_(True),
        )
        if requested_mapping_version is not None:
            query = query.filter(VendorFieldMapping.mapping_version == requested_mapping_version)
        mapping = query.order_by(VendorFieldMapping.mapping_version.desc()).first()
        if mapping is not None:
            mappings[group] = mapping
    return mappings


def _guidance_for_reason(reason: str) -> str | None:
    guidance = {
        "supplier_unverified": "Verify supplier identity before enrichment writes.",
        "unsupported_field": "Use a supported enrichment field or update field mapping contract.",
        "protected_field": "Field is immutable under current policy version.",
        "mapping_missing": "Create and activate vendor field mapping for this field group.",
        "mapping_not_ready": "Complete required mapping fields and mark mapping coverage as ready.",
        "alt_text_policy_preserve": "Set alt_text_policy=approved_overwrite to modify alt text.",
    }
    return guidance.get(reason)


def run_capability_audit(
    *,
    user_id: int,
    store_id: int,
    vendor_code: str,
    requested_fields: list[str],
    supplier_verified: bool,
    requested_mapping_version: int | None = None,
    alt_text_policy: str = "preserve",
) -> CapabilityAuditResult:
    """
    Compute deterministic allowed/blocked write plans before dry-run creation.
    """
    policy = _resolve_active_field_policy(store_id)
    immutable_policy_fields = set(policy.immutable_fields_json or []) if policy else set()
    protected_columns = tuple(
        sorted(set(PROTECTED_COLUMNS_DEFAULT).union(immutable_policy_fields))
    )
    policy_version = int(policy.policy_version) if policy else 1

    mappings_by_group = _resolve_mapping_by_group(
        store_id=store_id,
        vendor_code=vendor_code,
        requested_mapping_version=requested_mapping_version,
    )

    allowed: list[CapabilityDecision] = []
    blocked: list[CapabilityDecision] = []
    guidance_set: set[str] = set()
    resolved_mapping_version = requested_mapping_version

    for field_name in sorted(set(requested_fields)):
        group = FIELD_GROUP_BY_FIELD.get(field_name, "text")

        if not supplier_verified:
            reason = "supplier_unverified"
            blocked.append(
                CapabilityDecision(
                    field_name=field_name,
                    field_group=group,
                    allowed=False,
                    reason_code=reason,
                    detail="Supplier is not verified for enrichment writes.",
                )
            )
            guidance = _guidance_for_reason(reason)
            if guidance:
                guidance_set.add(guidance)
            continue

        if field_name not in SUPPORTED_MUTATION_FIELDS:
            reason = "unsupported_field"
            blocked.append(
                CapabilityDecision(
                    field_name=field_name,
                    field_group=group,
                    allowed=False,
                    reason_code=reason,
                    detail="Field is outside current enrichment write contract.",
                )
            )
            guidance = _guidance_for_reason(reason)
            if guidance:
                guidance_set.add(guidance)
            continue

        if field_name in protected_columns:
            reason = "protected_field"
            blocked.append(
                CapabilityDecision(
                    field_name=field_name,
                    field_group=group,
                    allowed=False,
                    reason_code=reason,
                    detail="Field is protected by immutable field policy.",
                )
            )
            guidance = _guidance_for_reason(reason)
            if guidance:
                guidance_set.add(guidance)
            continue

        if field_name == "alt_text" and alt_text_policy != "approved_overwrite":
            reason = "alt_text_policy_preserve"
            blocked.append(
                CapabilityDecision(
                    field_name=field_name,
                    field_group=group,
                    allowed=False,
                    reason_code=reason,
                    detail="Alt-text mutation requires explicit overwrite policy.",
                )
            )
            guidance = _guidance_for_reason(reason)
            if guidance:
                guidance_set.add(guidance)
            continue

        mapping = mappings_by_group.get(group)
        if mapping is None:
            reason = "mapping_missing"
            blocked.append(
                CapabilityDecision(
                    field_name=field_name,
                    field_group=group,
                    allowed=False,
                    reason_code=reason,
                    detail="No active vendor field mapping for this field group.",
                )
            )
            guidance = _guidance_for_reason(reason)
            if guidance:
                guidance_set.add(guidance)
            continue

        if mapping.coverage_status != "ready":
            reason = "mapping_not_ready"
            blocked.append(
                CapabilityDecision(
                    field_name=field_name,
                    field_group=group,
                    allowed=False,
                    reason_code=reason,
                    detail="Vendor field mapping exists but is not marked ready.",
                )
            )
            guidance = _guidance_for_reason(reason)
            if guidance:
                guidance_set.add(guidance)
            continue

        resolved_mapping_version = mapping.mapping_version
        allowed.append(
            CapabilityDecision(
                field_name=field_name,
                field_group=group,
                allowed=True,
                reason_code="allowed",
                detail="Field is permitted by scope, policy, and mapping contract.",
            )
        )

    return CapabilityAuditResult(
        store_id=store_id,
        user_id=user_id,
        vendor_code=vendor_code,
        supplier_verified=supplier_verified,
        policy_version=policy_version,
        mapping_version=resolved_mapping_version,
        alt_text_policy=alt_text_policy,
        protected_columns=protected_columns,
        generated_at=datetime.now(timezone.utc),
        allowed_write_plan=tuple(allowed),
        blocked_write_plan=tuple(blocked),
        upgrade_guidance=tuple(sorted(guidance_set)),
    )
