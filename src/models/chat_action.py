"""Chat action persistence model with idempotency lineage."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class ChatAction(db.Model, TimestampMixin):
    """Action proposal/execution lineage generated from chat messages."""

    __tablename__ = "chat_actions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('drafted', 'dry_run_ready', 'awaiting_approval', 'approved', "
            "'applying', 'completed', 'failed', 'conflicted', 'partial', 'cancelled')",
            name="chat_action_status",
        ),
        Index("ix_chat_action_session_status", "session_id", "status"),
    )

    id = db.Column(Integer, primary_key=True)
    session_id = db.Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    store_id = db.Column(
        Integer,
        ForeignKey("shopify_stores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    message_id = db.Column(
        Integer,
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action_type = db.Column(String(64), nullable=False)
    status = db.Column(String(64), nullable=False, default="drafted")
    idempotency_key = db.Column(String(128), nullable=True, unique=True, index=True)

    payload_json = db.Column(JSON, nullable=True)
    result_json = db.Column(JSON, nullable=True)
    error_message = db.Column(Text, nullable=True)

    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    applied_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    session = relationship("ChatSession", back_populates="actions")
    user = relationship("User")
    store = relationship("ShopifyStore")
    message = relationship("ChatMessage")

    def __repr__(self) -> str:
        return (
            f"<ChatAction id={self.id} session_id={self.session_id} "
            f"type={self.action_type} status={self.status}>"
        )
