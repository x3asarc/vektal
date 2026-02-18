"""Embedding linkage for assistant memory facts."""
from __future__ import annotations

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class AssistantMemoryEmbedding(db.Model, TimestampMixin):
    """Serialized vector payloads tied to typed memory facts."""

    __tablename__ = "assistant_memory_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "memory_fact_id",
            "embedding_model",
            "vector_version",
            name="uq_assistant_memory_embedding_version",
        ),
        Index("ix_assistant_memory_embedding_store_model", "store_id", "embedding_model"),
    )

    id = db.Column(Integer, primary_key=True)
    memory_fact_id = db.Column(
        Integer,
        ForeignKey("assistant_memory_facts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    store_id = db.Column(Integer, nullable=False, index=True)
    user_id = db.Column(Integer, nullable=True, index=True)
    embedding_json = db.Column(JSON, nullable=False)
    embedding_model = db.Column(String(96), nullable=False, default="placeholder")
    vector_version = db.Column(Integer, nullable=False, default=1)
    metadata_json = db.Column(JSON, nullable=True)

    memory_fact = relationship("AssistantMemoryFact", backref="embeddings")

    def __repr__(self) -> str:
        return (
            f"<AssistantMemoryEmbedding id={self.id} fact_id={self.memory_fact_id} "
            f"model={self.embedding_model}>"
        )

