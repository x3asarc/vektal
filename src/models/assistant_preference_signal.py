"""Human preference signal capture for Phase 13 instrumentation foundation."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class AssistantPreferenceSignal(db.Model, TimestampMixin):
    """Durable record of user feedback/edits on assistant-driven executions."""

    __tablename__ = "assistant_preference_signals"
    __table_args__ = (
        CheckConstraint(
            "tier IN ('tier_1', 'tier_2', 'tier_3')",
            name="assistant_preference_signal_tier",
        ),
        CheckConstraint(
            "signal_kind IN ('approval', 'edit', 'thumb')",
            name="assistant_preference_signal_kind",
        ),
        CheckConstraint(
            "preference_signal IN ("
            "'approved_all', 'approved_selection', 'edited', 'thumb_up', 'thumb_down', 'rejected'"
            ")",
            name="assistant_preference_signal_value",
        ),
        CheckConstraint(
            "selected_change_count >= 0",
            name="assistant_preference_signal_selected_count",
        ),
        CheckConstraint(
            "override_count >= 0",
            name="assistant_preference_signal_override_count",
        ),
        CheckConstraint(
            "reasoning_trace_tokens IS NULL OR reasoning_trace_tokens >= 0",
            name="assistant_preference_signal_tokens_nonnegative",
        ),
        CheckConstraint(
            "cost_usd IS NULL OR cost_usd >= 0",
            name="assistant_preference_signal_cost_nonnegative",
        ),
        Index("ix_assistant_preference_signal_action_created", "action_id", "created_at"),
        Index("ix_assistant_preference_signal_corr_created", "correlation_id", "created_at"),
        Index("ix_assistant_preference_signal_store_tier", "store_id", "tier"),
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

    correlation_id = db.Column(String(96), nullable=True, index=True)
    tier = db.Column(String(16), nullable=False, default="tier_1", index=True)
    signal_kind = db.Column(String(24), nullable=False, default="approval")
    preference_signal = db.Column(String(32), nullable=False, default="approved_all")

    selected_change_count = db.Column(Integer, nullable=False, default=0)
    override_count = db.Column(Integer, nullable=False, default=0)
    comment = db.Column(Text, nullable=True)
    reasoning_trace_tokens = db.Column(Integer, nullable=True)
    cost_usd = db.Column(db.Float, nullable=True)
    metadata_json = db.Column(JSON, nullable=True)

    action = relationship("ChatAction")
    session = relationship("ChatSession")
    store = relationship("ShopifyStore")
    user = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<AssistantPreferenceSignal id={self.id} action_id={self.action_id} "
            f"signal={self.preference_signal}>"
        )
