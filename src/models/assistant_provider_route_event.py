"""Provider route and fallback-stage telemetry persistence."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class AssistantProviderRouteEvent(db.Model, TimestampMixin):
    """Immutable provider route decision snapshots with correlation lineage."""

    __tablename__ = "assistant_provider_route_events"
    __table_args__ = (
        CheckConstraint(
            "route_stage IN ('primary', 'fallback', 'budget_guard', 'safe_degraded')",
            name="assistant_provider_route_event_stage",
        ),
        CheckConstraint(
            "fallback_reason_code IS NULL OR fallback_reason_code IN "
            "('none', 'provider_unavailable', 'invalid_tool_call', 'budget_guard', "
            "'policy_block', 'latency_guard')",
            name="assistant_provider_route_event_reason",
        ),
        Index("ix_assistant_provider_route_event_corr_created", "correlation_id", "created_at"),
        Index("ix_assistant_provider_route_event_store_created", "store_id", "created_at"),
    )

    id = db.Column(Integer, primary_key=True)
    correlation_id = db.Column(String(96), nullable=False, index=True)
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
    action_id = db.Column(
        Integer,
        ForeignKey("chat_actions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    route_event_id = db.Column(
        Integer,
        ForeignKey("assistant_route_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    intent_type = db.Column(String(64), nullable=False)
    route_stage = db.Column(String(32), nullable=False, default="primary")
    route_index = db.Column(Integer, nullable=False, default=0)
    selected_provider = db.Column(String(64), nullable=False)
    selected_model = db.Column(String(128), nullable=False)
    fallback_reason_code = db.Column(String(64), nullable=True, default="none")

    policy_snapshot_hash = db.Column(String(128), nullable=False, index=True)
    route_metadata_json = db.Column(JSON, nullable=True)

    user = relationship("User")
    store = relationship("ShopifyStore")
    session = relationship("ChatSession")
    action = relationship("ChatAction")
    route_event = relationship("AssistantRouteEvent")

    def __repr__(self) -> str:
        return (
            f"<AssistantProviderRouteEvent id={self.id} corr={self.correlation_id} "
            f"provider={self.selected_provider} stage={self.route_stage}>"
        )

