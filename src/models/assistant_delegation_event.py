"""Tier-3 delegation lineage events."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class AssistantDelegationEvent(db.Model, TimestampMixin):
    """Manager-worker delegation event with immutable worker scope snapshot."""

    __tablename__ = "assistant_delegation_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('spawned', 'running', 'completed', 'failed', 'blocked')",
            name="assistant_delegation_event_status",
        ),
        Index("ix_assistant_delegation_parent", "parent_request_id"),
        Index("ix_assistant_delegation_action_created", "action_id", "created_at"),
    )

    id = db.Column(Integer, primary_key=True)
    session_id = db.Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action_id = db.Column(
        Integer,
        ForeignKey("chat_actions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    store_id = db.Column(
        Integer,
        ForeignKey("shopify_stores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parent_request_id = db.Column(String(64), nullable=True)
    request_id = db.Column(String(64), nullable=False, unique=True, index=True)
    depth = db.Column(Integer, nullable=False, default=1)
    fan_out = db.Column(Integer, nullable=False, default=1)
    status = db.Column(String(16), nullable=False, default="spawned")
    worker_tool_scope_json = db.Column(JSON, nullable=False, default=list)
    budget_json = db.Column(JSON, nullable=True)
    fallback_stage = db.Column(String(64), nullable=True)
    reason = db.Column(Text, nullable=True)
    metadata_json = db.Column(JSON, nullable=True)

    session = relationship("ChatSession")
    action = relationship("ChatAction")
    user = relationship("User")
    store = relationship("ShopifyStore")

    def __repr__(self) -> str:
        return (
            f"<AssistantDelegationEvent id={self.id} request_id={self.request_id} "
            f"status={self.status}>"
        )

