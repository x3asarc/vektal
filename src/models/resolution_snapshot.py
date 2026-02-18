"""Batch and per-product snapshots for resolution safety guarantees."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class ResolutionSnapshot(db.Model, TimestampMixin):
    """Immutable snapshot payload captured before apply mutations."""

    __tablename__ = "resolution_snapshots"
    __table_args__ = (
        CheckConstraint(
            "snapshot_type IN ('baseline', 'batch_manifest', 'product_pre_change')",
            name="resolution_snapshot_type",
        ),
        Index("ix_resolution_snapshot_batch_type", "batch_id", "snapshot_type"),
        Index("ix_resolution_snapshot_item", "item_id"),
        Index("ix_resolution_snapshot_checksum_type", "checksum", "snapshot_type"),
    )

    id = db.Column(Integer, primary_key=True)
    batch_id = db.Column(
        Integer,
        ForeignKey("resolution_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id = db.Column(
        Integer,
        ForeignKey("resolution_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    snapshot_type = db.Column(String(64), nullable=False)
    checksum = db.Column(String(128), nullable=True, index=True)
    canonical_snapshot_id = db.Column(
        Integer,
        ForeignKey("resolution_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    retention_expires_at = db.Column(DateTime(timezone=True), nullable=True)
    payload = db.Column(JSON, nullable=False)

    batch = relationship("ResolutionBatch", backref="snapshots")
    item = relationship("ResolutionItem", backref="snapshots")
    canonical_snapshot = relationship("ResolutionSnapshot", remote_side=[id], uselist=False)

    def __repr__(self) -> str:
        return f"<ResolutionSnapshot id={self.id} batch_id={self.batch_id} type={self.snapshot_type}>"
