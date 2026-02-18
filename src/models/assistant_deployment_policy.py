"""Deployment policy persistence for provider ladder and rollout guards."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


def _default_provider_ladder() -> list[dict]:
    return [
        {"provider": "qwen", "model": "qwen-2.5-coder", "tier_scope": "tier_1,tier_2"},
        {"provider": "openrouter", "model": "anthropic/claude-3.5-sonnet", "tier_scope": "tier_2,tier_3"},
        {"provider": "openrouter", "model": "openai/gpt-4o", "tier_scope": "tier_3"},
    ]


def _default_rollout_guard() -> dict:
    return {
        "canary_drop_threshold": 0.05,
        "sample_floor": 100,
        "availability_target": 0.999,
        "error_budget_seconds_30d": 2592,
    }


class AssistantDeploymentPolicy(db.Model, TimestampMixin):
    """Versioned deployment policy object for provider routing and canary gates."""

    __tablename__ = "assistant_deployment_policies"
    __table_args__ = (
        CheckConstraint(
            "scope_kind IN ('global', 'tenant')",
            name="assistant_deployment_policy_scope_kind",
        ),
        CheckConstraint(
            "(scope_kind = 'global' AND store_id IS NULL) OR "
            "(scope_kind = 'tenant' AND store_id IS NOT NULL)",
            name="assistant_deployment_policy_scope_store_match",
        ),
        CheckConstraint(
            "policy_version >= 1",
            name="assistant_deployment_policy_version",
        ),
        UniqueConstraint(
            "scope_kind",
            "store_id",
            "policy_version",
            name="uq_assistant_deployment_policy_scope_version",
        ),
        Index("ix_assistant_deployment_policy_scope_active", "scope_kind", "store_id", "is_active"),
    )

    id = db.Column(Integer, primary_key=True)
    scope_kind = db.Column(String(16), nullable=False, default="global")
    store_id = db.Column(
        Integer,
        ForeignKey("shopify_stores.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    policy_version = db.Column(Integer, nullable=False, default=1)
    is_active = db.Column(Boolean, nullable=False, default=True, index=True)
    effective_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    changed_by_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    primary_provider = db.Column(String(64), nullable=False, default="qwen")
    primary_model = db.Column(String(128), nullable=False, default="qwen-2.5-coder")
    provider_ladder_json = db.Column(JSON, nullable=False, default=_default_provider_ladder)
    budget_guard_percent = db.Column(db.Float, nullable=False, default=95.0)
    rollout_guard_json = db.Column(JSON, nullable=False, default=_default_rollout_guard)
    metadata_json = db.Column(JSON, nullable=True)

    store = relationship("ShopifyStore")
    changed_by = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<AssistantDeploymentPolicy id={self.id} scope={self.scope_kind} "
            f"store_id={self.store_id} version={self.policy_version}>"
        )

