"""Recovery log entries for stale/deleted targets or blocked apply operations."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class RecoveryLog(db.Model, TimestampMixin):
    """Stores recoverable context for non-applied conflicts."""

    __tablename__ = "recovery_logs"
    __table_args__ = (
        CheckConstraint(
            "reason_code IN ('stale_target', 'deleted_target', 'preflight_conflict', "
            "'critical_apply_failure', 'policy_exclusion')",
            name="recovery_log_reason",
        ),
        Index("ix_recovery_log_batch_reason", "batch_id", "reason_code"),
        Index("ix_recovery_log_store_created", "store_id", "created_at"),
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
        ForeignKey("resolution_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    store_id = db.Column(
        Integer,
        ForeignKey("shopify_stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason_code = db.Column(String(64), nullable=False)
    reason_detail = db.Column(Text, nullable=True)
    payload = db.Column(JSON, nullable=False)
    replay_metadata = db.Column(JSON, nullable=True)
    deferred_until = db.Column(DateTime(timezone=True), nullable=True)
    snapshot_id = db.Column(
        Integer,
        ForeignKey("resolution_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_user_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    batch = relationship("ResolutionBatch", backref="recovery_logs")
    item = relationship("ResolutionItem")
    snapshot = relationship("ResolutionSnapshot")
    store = relationship("ShopifyStore", backref="recovery_logs")
    created_by = relationship("User")

    def __repr__(self) -> str:
        return f"<RecoveryLog id={self.id} batch_id={self.batch_id} reason={self.reason_code}>"
