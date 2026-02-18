"""Post-execution verification event lineage for governance finality contracts."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


def _default_poll_schedule() -> list[int]:
    return [5, 10, 15]


class AssistantVerificationEvent(db.Model, TimestampMixin):
    """Durable verification results for action/batch execution finality."""

    __tablename__ = "assistant_verification_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('verified', 'deferred', 'failed')",
            name="assistant_verification_event_status",
        ),
        CheckConstraint(
            "attempt_count >= 1",
            name="assistant_verification_event_attempt_count",
        ),
        CheckConstraint(
            "(status = 'verified' AND verified_at IS NOT NULL) OR "
            "(status != 'verified')",
            name="assistant_verification_event_verified_at_required",
        ),
        Index("ix_assistant_verification_event_store_status", "store_id", "status"),
        Index("ix_assistant_verification_event_action_created", "action_id", "created_at"),
    )

    id = db.Column(Integer, primary_key=True)
    action_id = db.Column(
        Integer,
        ForeignKey("chat_actions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    batch_id = db.Column(
        Integer,
        ForeignKey("resolution_batches.id", ondelete="SET NULL"),
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
    oracle_name = db.Column(String(64), nullable=False, default="post_apply_finality")
    status = db.Column(String(16), nullable=False, default="deferred", index=True)
    attempt_count = db.Column(Integer, nullable=False, default=1)
    poll_schedule_json = db.Column(JSON, nullable=False, default=_default_poll_schedule)
    waited_seconds = db.Column(Integer, nullable=False, default=0)
    status_message = db.Column(String(255), nullable=True)
    oracle_result_json = db.Column(JSON, nullable=True)
    metadata_json = db.Column(JSON, nullable=True)

    deferred_until = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    verified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    failed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    action = relationship("ChatAction")
    batch = relationship("ResolutionBatch")
    store = relationship("ShopifyStore")
    user = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<AssistantVerificationEvent id={self.id} action_id={self.action_id} "
            f"status={self.status}>"
        )

    @staticmethod
    def utcnow() -> datetime:
        return datetime.now(timezone.utc)

