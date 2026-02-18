"""Tenant-specific tool policy overlays."""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class AssistantTenantToolPolicy(db.Model, TimestampMixin):
    """Allow/deny policy overlay scoped to tenant store."""

    __tablename__ = "assistant_tenant_tool_policies"
    __table_args__ = (
        CheckConstraint(
            "policy_action IN ('allow', 'deny')",
            name="assistant_tenant_tool_policy_action",
        ),
        UniqueConstraint(
            "store_id",
            "tool_id",
            "role_scope",
            name="uq_assistant_tenant_tool_policy_scope",
        ),
        Index("ix_assistant_tenant_policy_store_tool", "store_id", "tool_id"),
    )

    id = db.Column(Integer, primary_key=True)
    store_id = db.Column(
        Integer,
        ForeignKey("shopify_stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_id = db.Column(String(96), nullable=False, index=True)
    policy_action = db.Column(String(16), nullable=False, default="deny")
    role_scope = db.Column(String(64), nullable=True)
    is_active = db.Column(Boolean, nullable=False, default=True)
    metadata_json = db.Column(JSON, nullable=True)
    created_by_user_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    store = relationship("ShopifyStore", backref="assistant_tool_policies")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    def __repr__(self) -> str:
        return (
            f"<AssistantTenantToolPolicy store_id={self.store_id} "
            f"tool_id={self.tool_id} action={self.policy_action}>"
        )

