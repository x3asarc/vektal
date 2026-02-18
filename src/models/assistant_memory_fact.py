"""Typed assistant memory facts for scoped retrieval."""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class AssistantMemoryFact(db.Model, TimestampMixin):
    """Tenant and user-scoped memory facts with provenance and trust score."""

    __tablename__ = "assistant_memory_facts"
    __table_args__ = (
        CheckConstraint(
            "trust_score >= 0.0 AND trust_score <= 1.0",
            name="assistant_memory_fact_trust_score",
        ),
        Index("ix_assistant_memory_fact_store_active", "store_id", "is_active"),
        Index("ix_assistant_memory_fact_user_key", "user_id", "fact_key"),
    )

    id = db.Column(Integer, primary_key=True)
    store_id = db.Column(
        Integer,
        ForeignKey("shopify_stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fact_key = db.Column(String(128), nullable=False, index=True)
    fact_value_text = db.Column(Text, nullable=False)
    fact_value_json = db.Column(JSON, nullable=True)
    source = db.Column(String(64), nullable=False, default="chat")
    trust_score = db.Column(db.Float, nullable=False, default=0.5)
    provenance_json = db.Column(JSON, nullable=True)
    is_active = db.Column(Boolean, nullable=False, default=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    last_used_at = db.Column(db.DateTime(timezone=True), nullable=True)

    store = relationship("ShopifyStore", backref="assistant_memory_facts")
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<AssistantMemoryFact id={self.id} key={self.fact_key}>"

