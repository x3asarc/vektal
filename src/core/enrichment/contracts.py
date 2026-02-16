"""Core contracts for capability auditing and dry-run enrichment planning."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


PROTECTED_COLUMNS_DEFAULT = (
    "id",
    "store_id",
    "shopify_product_id",
    "shopify_variant_id",
    "created_at",
    "updated_at",
)

FIELD_GROUP_BY_FIELD = {
    "title": "text",
    "description": "text",
    "product_type": "text",
    "tags": "text",
    "price": "pricing",
    "compare_at_price": "pricing",
    "sku": "ids",
    "barcode": "ids",
    "image_url": "images",
    "alt_text": "images",
    "metafield.color": "metadata",
    "metafield.finish": "metadata",
    "metafield.material": "metadata",
}

SUPPORTED_MUTATION_FIELDS = frozenset(FIELD_GROUP_BY_FIELD.keys())


@dataclass(frozen=True)
class RequestedField:
    """Field requested for enrichment write planning."""

    field_name: str
    field_group: str


@dataclass(frozen=True)
class RequestedMutation:
    """One proposed field mutation in dry-run planning."""

    product_id: int
    field_name: str
    proposed_value: Any
    current_value: Any = None
    confidence: float | None = None
    provenance: dict[str, Any] | None = None

    @property
    def field_group(self) -> str:
        return FIELD_GROUP_BY_FIELD.get(self.field_name, "text")


@dataclass(frozen=True)
class CapabilityDecision:
    """Allowed/blocked decision for one field."""

    field_name: str
    field_group: str
    allowed: bool
    reason_code: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "field_group": self.field_group,
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class CapabilityAuditResult:
    """Result of store/vendor capability and policy preflight."""

    store_id: int
    user_id: int
    vendor_code: str
    supplier_verified: bool
    policy_version: int
    mapping_version: int | None
    alt_text_policy: str
    protected_columns: tuple[str, ...]
    generated_at: datetime
    allowed_write_plan: tuple[CapabilityDecision, ...] = field(default_factory=tuple)
    blocked_write_plan: tuple[CapabilityDecision, ...] = field(default_factory=tuple)
    upgrade_guidance: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "store_id": self.store_id,
            "user_id": self.user_id,
            "vendor_code": self.vendor_code,
            "supplier_verified": self.supplier_verified,
            "policy_version": self.policy_version,
            "mapping_version": self.mapping_version,
            "alt_text_policy": self.alt_text_policy,
            "protected_columns": list(self.protected_columns),
            "generated_at": self.generated_at.isoformat(),
            "allowed_write_plan": [entry.to_dict() for entry in self.allowed_write_plan],
            "blocked_write_plan": [entry.to_dict() for entry in self.blocked_write_plan],
            "upgrade_guidance": list(self.upgrade_guidance),
        }


@dataclass(frozen=True)
class WriteIntent:
    """Deterministic dry-run write intent output."""

    product_id: int
    field_name: str
    field_group: str
    before_value: Any
    after_value: Any
    policy_version: int
    mapping_version: int | None
    reason_codes: tuple[str, ...]
    requires_user_action: bool
    is_blocked: bool
    is_protected_column: bool
    alt_text_preserved: bool
    confidence: float | None = None
    provenance: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "field_name": self.field_name,
            "field_group": self.field_group,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "policy_version": self.policy_version,
            "mapping_version": self.mapping_version,
            "reason_codes": list(self.reason_codes),
            "requires_user_action": self.requires_user_action,
            "is_blocked": self.is_blocked,
            "is_protected_column": self.is_protected_column,
            "alt_text_preserved": self.alt_text_preserved,
            "confidence": self.confidence,
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class DryRunWritePlan:
    """Compiled deterministic write plan with allowed and blocked intents."""

    allowed: tuple[WriteIntent, ...]
    blocked: tuple[WriteIntent, ...]

    @property
    def counts(self) -> dict[str, int]:
        return {
            "allowed": len(self.allowed),
            "blocked": len(self.blocked),
            "total": len(self.allowed) + len(self.blocked),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": [item.to_dict() for item in self.allowed],
            "blocked": [item.to_dict() for item in self.blocked],
            "counts": self.counts,
        }
