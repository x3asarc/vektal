"""Resolution batch + item + field-change persistence."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class ResolutionBatch(db.Model, TimestampMixin):
    """A single dry-run / apply batch lifecycle."""

    __tablename__ = "resolution_batches"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'ready_for_review', 'approved', 'scheduled', 'applying', "
            "'applied', 'applied_with_conflicts', 'failed', 'cancelled')",
            name="resolution_batch_status",
        ),
        CheckConstraint("apply_mode IN ('immediate', 'scheduled')", name="resolution_batch_apply_mode"),
        Index("ix_resolution_batch_user_status", "user_id", "status"),
        Index("ix_resolution_batch_store_status", "store_id", "status"),
    )

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    store_id = db.Column(
        Integer,
        ForeignKey("shopify_stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = db.Column(String(64), nullable=False, default="draft")
    apply_mode = db.Column(String(32), nullable=False, default="immediate")
    scheduled_for = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    applied_at = db.Column(db.DateTime(timezone=True), nullable=True)
    critical_error_threshold = db.Column(Integer, nullable=False, default=3)

    # Checkout lock
    lock_owner_user_id = db.Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    lock_expires_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    lock_heartbeat_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Attribution
    created_by_user_id = db.Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_user_id = db.Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    metadata_json = db.Column(JSON, nullable=True)

    user = relationship("User", foreign_keys=[user_id], backref="resolution_batches")
    store = relationship("ShopifyStore", backref="resolution_batches")
    lock_owner = relationship("User", foreign_keys=[lock_owner_user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])

    items = relationship(
        "ResolutionItem",
        back_populates="batch",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="ResolutionItem.id",
    )

    def __repr__(self) -> str:
        return f"<ResolutionBatch id={self.id} store_id={self.store_id} status={self.status}>"


class ResolutionItem(db.Model, TimestampMixin):
    """Per-product record inside a resolution batch."""

    __tablename__ = "resolution_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'ready', 'awaiting_approval', 'approved', "
            "'structural_conflict', 'excluded', 'applied', 'failed')",
            name="resolution_item_status",
        ),
        Index("ix_resolution_item_batch_status", "batch_id", "status"),
        Index("ix_resolution_item_product", "product_id"),
    )

    id = db.Column(Integer, primary_key=True)
    batch_id = db.Column(
        Integer,
        ForeignKey("resolution_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = db.Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    shopify_product_id = db.Column(db.BigInteger, nullable=True, index=True)
    shopify_variant_id = db.Column(db.BigInteger, nullable=True, index=True)
    supplier_code = db.Column(String(64), nullable=True, index=True)

    status = db.Column(String(64), nullable=False, default="pending")
    structural_state = db.Column(String(128), nullable=True)
    conflict_reason = db.Column(Text, nullable=True)
    product_label = db.Column(String(512), nullable=True)

    batch = relationship("ResolutionBatch", back_populates="items")
    product = relationship("Product")
    changes = relationship(
        "ResolutionChange",
        back_populates="item",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="ResolutionChange.id",
    )

    def __repr__(self) -> str:
        return f"<ResolutionItem id={self.id} batch_id={self.batch_id} status={self.status}>"


class ResolutionChange(db.Model, TimestampMixin):
    """Field-level proposed change + decision state."""

    __tablename__ = "resolution_changes"
    __table_args__ = (
        CheckConstraint(
            "field_group IN ('images', 'text', 'pricing', 'ids')",
            name="resolution_change_field_group",
        ),
        CheckConstraint(
            "status IN ('auto_applied', 'awaiting_approval', 'approved', 'rejected', "
            "'blocked_exclusion', 'structural_conflict', 'applied', 'failed')",
            name="resolution_change_status",
        ),
        Index("ix_resolution_change_item_status", "item_id", "status"),
        Index("ix_resolution_change_field", "field_name"),
    )

    id = db.Column(Integer, primary_key=True)
    item_id = db.Column(
        Integer,
        ForeignKey("resolution_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_group = db.Column(String(32), nullable=False)
    field_name = db.Column(String(128), nullable=False)

    before_value = db.Column(JSON, nullable=True)
    after_value = db.Column(JSON, nullable=True)

    reason_sentence = db.Column(Text, nullable=True)
    reason_factors = db.Column(JSON, nullable=True)
    confidence_score = db.Column(Numeric(4, 3), nullable=True)

    status = db.Column(String(64), nullable=False, default="awaiting_approval")

    applied_rule_id = db.Column(
        Integer,
        ForeignKey("resolution_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    blocked_by_rule_id = db.Column(
        Integer,
        ForeignKey("resolution_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_by_user_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    item = relationship("ResolutionItem", back_populates="changes")
    applied_rule = relationship("ResolutionRule", foreign_keys=[applied_rule_id])
    blocked_rule = relationship("ResolutionRule", foreign_keys=[blocked_by_rule_id])
    approved_by = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<ResolutionChange id={self.id} item_id={self.item_id} "
            f"field={self.field_name} status={self.status}>"
        )

