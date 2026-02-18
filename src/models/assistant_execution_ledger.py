"""Idempotency ledger for terminal replay-safe execution semantics."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class AssistantExecutionLedger(db.Model, TimestampMixin):
    """Durable idempotency ledger with terminal execution states."""

    __tablename__ = "assistant_execution_ledger"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PROCESSING', 'SUCCESS', 'FAILED', 'EXPIRED')",
            name="assistant_execution_ledger_status",
        ),
        CheckConstraint(
            "attempt_count >= 1",
            name="assistant_execution_ledger_attempt_count",
        ),
        Index("ix_assistant_execution_ledger_store_status", "store_id", "status"),
    )

    id = db.Column(Integer, primary_key=True)
    idempotency_key = db.Column(String(128), nullable=False, unique=True, index=True)

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

    action_type = db.Column(String(96), nullable=False, index=True)
    resource_id = db.Column(String(128), nullable=True, index=True)
    payload_hash = db.Column(String(64), nullable=False)
    correlation_id = db.Column(String(96), nullable=True)
    policy_snapshot_hash = db.Column(String(128), nullable=True)

    status = db.Column(String(16), nullable=False, default="PROCESSING", index=True)
    status_url = db.Column(String(255), nullable=True)
    response_json = db.Column(JSON, nullable=True)
    metadata_json = db.Column(JSON, nullable=True)
    error_message = db.Column(Text, nullable=True)
    last_error_class = db.Column(String(64), nullable=True)
    attempt_count = db.Column(Integer, nullable=False, default=1)

    started_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)

    store = relationship("ShopifyStore")
    user = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<AssistantExecutionLedger id={self.id} key={self.idempotency_key} "
            f"status={self.status} attempts={self.attempt_count}>"
        )
