"""Oracle verification signal capture for Phase 13 instrumentation foundation."""
from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class AssistantVerificationSignal(db.Model, TimestampMixin):
    """Durable binary oracle outcome linked to assistant execution lineage."""

    __tablename__ = "assistant_verification_signals"
    __table_args__ = (
        CheckConstraint(
            "tier IN ('tier_1', 'tier_2', 'tier_3')",
            name="assistant_verification_signal_tier",
        ),
        CheckConstraint(
            "verification_status IN ('verified', 'deferred', 'failed')",
            name="assistant_verification_signal_status",
        ),
        CheckConstraint(
            "attempt_count >= 1",
            name="assistant_verification_signal_attempt_count",
        ),
        CheckConstraint(
            "waited_seconds >= 0",
            name="assistant_verification_signal_waited_nonnegative",
        ),
        CheckConstraint(
            "reasoning_trace_tokens IS NULL OR reasoning_trace_tokens >= 0",
            name="assistant_verification_signal_tokens_nonnegative",
        ),
        CheckConstraint(
            "cost_usd IS NULL OR cost_usd >= 0",
            name="assistant_verification_signal_cost_nonnegative",
        ),
        Index("ix_assistant_verification_signal_action_created", "action_id", "created_at"),
        Index("ix_assistant_verification_signal_corr_created", "correlation_id", "created_at"),
        Index("ix_assistant_verification_signal_store_tier", "store_id", "tier"),
    )

    id = db.Column(Integer, primary_key=True)
    action_id = db.Column(
        Integer,
        ForeignKey("chat_actions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id = db.Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    store_id = db.Column(
        Integer,
        ForeignKey("shopify_stores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    verification_event_id = db.Column(
        Integer,
        ForeignKey("assistant_verification_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    correlation_id = db.Column(String(96), nullable=False, index=True)
    tier = db.Column(String(16), nullable=False, default="tier_1", index=True)
    verification_status = db.Column(String(16), nullable=False, default="deferred")
    oracle_signal = db.Column(Boolean, nullable=False, default=False)
    attempt_count = db.Column(Integer, nullable=False, default=1)
    waited_seconds = db.Column(Integer, nullable=False, default=0)
    reasoning_trace_tokens = db.Column(Integer, nullable=True)
    cost_usd = db.Column(db.Float, nullable=True)
    metadata_json = db.Column(JSON, nullable=True)

    action = relationship("ChatAction")
    session = relationship("ChatSession")
    store = relationship("ShopifyStore")
    user = relationship("User")
    verification_event = relationship("AssistantVerificationEvent")

    def __repr__(self) -> str:
        return (
            f"<AssistantVerificationSignal id={self.id} action_id={self.action_id} "
            f"status={self.verification_status} oracle={self.oracle_signal}>"
        )
