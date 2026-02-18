"""Global and tenant kill-switch controls for fail-closed execution."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class AssistantKillSwitch(db.Model, TimestampMixin):
    """Governance kill-switch scoped globally or per tenant."""

    __tablename__ = "assistant_kill_switches"
    __table_args__ = (
        CheckConstraint(
            "scope_kind IN ('global', 'tenant')",
            name="assistant_kill_switch_scope_kind",
        ),
        CheckConstraint(
            "mode IN ('safe_degraded', 'blocked')",
            name="assistant_kill_switch_mode",
        ),
        CheckConstraint(
            "(scope_kind = 'global' AND store_id IS NULL) OR "
            "(scope_kind = 'tenant' AND store_id IS NOT NULL)",
            name="assistant_kill_switch_scope_store_match",
        ),
        Index("ix_assistant_kill_switch_scope_enabled", "scope_kind", "is_enabled", "effective_at"),
        Index("ix_assistant_kill_switch_store_enabled", "store_id", "is_enabled"),
    )

    id = db.Column(Integer, primary_key=True)
    scope_kind = db.Column(String(16), nullable=False, default="tenant")
    store_id = db.Column(
        Integer,
        ForeignKey("shopify_stores.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    mode = db.Column(String(32), nullable=False, default="safe_degraded")
    is_enabled = db.Column(Boolean, nullable=False, default=True, index=True)

    reason = db.Column(Text, nullable=True)
    metadata_json = db.Column(JSON, nullable=True)
    changed_by_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    effective_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    store = relationship("ShopifyStore")
    changed_by = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<AssistantKillSwitch id={self.id} scope={self.scope_kind} "
            f"store_id={self.store_id} enabled={self.is_enabled}>"
        )

