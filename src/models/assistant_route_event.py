"""Auditable routing decision events."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class AssistantRouteEvent(db.Model, TimestampMixin):
    """Immutable routing event snapshot for explainability and audit."""

    __tablename__ = "assistant_route_events"
    __table_args__ = (
        CheckConstraint(
            "route_decision IN ('tier_1', 'tier_2', 'tier_3', 'blocked')",
            name="assistant_route_event_route_decision",
        ),
        Index("ix_assistant_route_event_store_created", "store_id", "created_at"),
        Index("ix_assistant_route_event_user_created", "user_id", "created_at"),
    )

    id = db.Column(Integer, primary_key=True)
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
    session_id = db.Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    route_decision = db.Column(String(16), nullable=False)
    intent_type = db.Column(String(64), nullable=False)
    classifier_method = db.Column(String(32), nullable=False, default="heuristic")
    confidence = db.Column(db.Float, nullable=False, default=0.0)
    approval_mode = db.Column(String(64), nullable=False, default="none")
    fallback_stage = db.Column(String(64), nullable=True)
    reasons_json = db.Column(JSON, nullable=False, default=list)
    effective_toolset_json = db.Column(JSON, nullable=False, default=list)
    policy_snapshot_hash = db.Column(String(128), nullable=False, index=True)
    effective_toolset_hash = db.Column(String(128), nullable=False, index=True)
    metadata_json = db.Column(JSON, nullable=True)

    user = relationship("User")
    store = relationship("ShopifyStore")
    session = relationship("ChatSession")

    def __repr__(self) -> str:
        return (
            f"<AssistantRouteEvent id={self.id} decision={self.route_decision} "
            f"intent={self.intent_type}>"
        )

