"""Chat message persistence model."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class ChatMessage(db.Model, TimestampMixin):
    """Stored chat message with deterministic typed blocks for rendering."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="chat_message_role"),
        Index("ix_chat_message_session_role", "session_id", "role"),
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

    role = db.Column(String(32), nullable=False)
    content = db.Column(Text, nullable=False)
    blocks_json = db.Column(JSON, nullable=False, default=list)
    source_metadata = db.Column(JSON, nullable=True)

    intent_type = db.Column(String(64), nullable=True)
    classification_method = db.Column(String(32), nullable=True)
    confidence = db.Column(db.Numeric(4, 3), nullable=True)

    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} session_id={self.session_id} role={self.role}>"
