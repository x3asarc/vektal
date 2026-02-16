"""Deterministic dry-run write-plan compiler for enrichment mutations."""
from __future__ import annotations

from src.core.enrichment.contracts import CapabilityAuditResult, DryRunWritePlan, RequestedMutation, WriteIntent


def _decision_lookup(audit: CapabilityAuditResult) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for item in audit.allowed_write_plan:
        lookup[item.field_name] = item.reason_code
    for item in audit.blocked_write_plan:
        lookup[item.field_name] = item.reason_code
    return lookup


def compile_write_plan(
    *,
    audit: CapabilityAuditResult,
    proposed_mutations: list[RequestedMutation],
) -> DryRunWritePlan:
    """Compile stable allowed/blocked intents from audit + requested mutations."""
    allowed_field_names = {item.field_name for item in audit.allowed_write_plan}
    blocked_field_names = {item.field_name for item in audit.blocked_write_plan}
    reason_by_field = _decision_lookup(audit)

    allowed: list[WriteIntent] = []
    blocked: list[WriteIntent] = []

    ordered_mutations = sorted(proposed_mutations, key=lambda row: (row.product_id, row.field_name))
    for mutation in ordered_mutations:
        field_name = mutation.field_name
        is_protected = field_name in audit.protected_columns
        alt_text_preserved = not (field_name == "alt_text" and audit.alt_text_policy != "approved_overwrite")

        reason_codes: list[str] = []
        if field_name in blocked_field_names:
            reason_codes.append(reason_by_field.get(field_name, "blocked"))
        elif field_name not in allowed_field_names:
            reason_codes.append("not_in_allowed_write_plan")
        else:
            reason_codes.append("allowed")

        if is_protected and "protected_field" not in reason_codes:
            reason_codes.append("protected_field")
        if not alt_text_preserved and "alt_text_policy_preserve" not in reason_codes:
            reason_codes.append("alt_text_policy_preserve")

        is_blocked = any(
            code in {"protected_field", "alt_text_policy_preserve", "not_in_allowed_write_plan"}
            or code.startswith("mapping_")
            or code == "supplier_unverified"
            for code in reason_codes
        )

        intent = WriteIntent(
            product_id=mutation.product_id,
            field_name=field_name,
            field_group=mutation.field_group,
            before_value=mutation.current_value,
            after_value=mutation.proposed_value,
            policy_version=audit.policy_version,
            mapping_version=audit.mapping_version,
            reason_codes=tuple(reason_codes),
            requires_user_action=True,
            is_blocked=is_blocked,
            is_protected_column=is_protected,
            alt_text_preserved=alt_text_preserved,
            confidence=mutation.confidence,
            provenance=mutation.provenance,
        )

        if is_blocked:
            blocked.append(intent)
        else:
            allowed.append(intent)

    return DryRunWritePlan(allowed=tuple(allowed), blocked=tuple(blocked))
