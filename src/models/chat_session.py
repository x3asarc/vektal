"""Chat session persistence model."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class ChatSession(db.Model, TimestampMixin):
    """Conversation session scoped to a user and optional store."""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        CheckConstraint("state IN ('at_door', 'in_house')", name="chat_session_state"),
        CheckConstraint("status IN ('active', 'closed')", name="chat_session_status"),
        Index("ix_chat_session_user_state", "user_id", "state"),
        Index("ix_chat_session_user_status", "user_id", "status"),
    )

    id = db.Column(Integer, primary_key=True)
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

    title = db.Column(String(255), nullable=True)
    state = db.Column(String(32), nullable=False, default="at_door")
    status = db.Column(String(32), nullable=False, default="active")
    summary = db.Column(Text, nullable=True)
    context_json = db.Column(JSON, nullable=True)
    last_message_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    user = relationship("User", backref="chat_sessions")
    store = relationship("ShopifyStore", backref="chat_sessions")

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="ChatMessage.created_at",
    )
    actions = relationship(
        "ChatAction",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="ChatAction.created_at",
    )

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} user_id={self.user_id} state={self.state}>"
