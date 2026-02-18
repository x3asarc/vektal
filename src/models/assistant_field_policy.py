"""Tenant field protection and HITL threshold policy contracts."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


def _default_immutable_fields() -> list[str]:
    return ["store_currency", "admin_email", "tenant_id"]


def _default_hitl_thresholds() -> dict:
    return {
        "inventory_change_absolute": 100,
        "price_change_percent": 15.0,
    }


def _default_dr_objectives() -> dict:
    return {
        "single_tenant_rto_seconds": 120,
        "single_tenant_rpo_seconds": 300,
        "full_system_rto_seconds": 3600,
        "full_system_rpo_seconds": 21600,
    }


class AssistantFieldPolicy(db.Model, TimestampMixin):
    """Tenant-specific immutable field and escalation threshold policy."""

    __tablename__ = "assistant_field_policies"
    __table_args__ = (
        CheckConstraint(
            "policy_version >= 1",
            name="assistant_field_policy_version",
        ),
        UniqueConstraint(
            "store_id",
            "policy_version",
            name="uq_assistant_field_policy_store_version",
        ),
        Index("ix_assistant_field_policy_store_active", "store_id", "is_active", "effective_at"),
    )

    id = db.Column(Integer, primary_key=True)
    store_id = db.Column(
        Integer,
        ForeignKey("shopify_stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_name = db.Column(String(96), nullable=False, default="default")
    policy_version = db.Column(Integer, nullable=False, default=1)
    is_active = db.Column(Boolean, nullable=False, default=True, index=True)
    effective_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    immutable_fields_json = db.Column(JSON, nullable=False, default=_default_immutable_fields)
    hitl_thresholds_json = db.Column(JSON, nullable=False, default=_default_hitl_thresholds)
    dr_objectives_json = db.Column(JSON, nullable=False, default=_default_dr_objectives)
    metadata_json = db.Column(JSON, nullable=True)

    changed_by_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    store = relationship("ShopifyStore", backref="assistant_field_policies")
    changed_by = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<AssistantFieldPolicy id={self.id} store_id={self.store_id} "
            f"version={self.policy_version} active={self.is_active}>"
        )

