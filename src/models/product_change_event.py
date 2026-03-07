"""Product change lineage model for precision workspace history/diff views."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class ProductChangeEvent(db.Model, TimestampMixin):
    """Append-only product change event for audit-grade lineage."""

    __tablename__ = "product_change_events"
    __table_args__ = (
        CheckConstraint(
            "source IN ('workspace', 'chat', 'system', 'import')",
            name="product_change_event_source",
        ),
        CheckConstraint(
            "event_type IN ('manual_edit', 'bulk_stage', 'dry_run_compile', 'apply', 'rollback')",
            name="product_change_event_type",
        ),
        Index("ix_product_change_event_product_created", "product_id", "created_at"),
        Index("ix_product_change_event_store_created", "store_id", "created_at"),
    )

    id = db.Column(Integer, primary_key=True)
    product_id = db.Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    store_id = db.Column(
        Integer,
        ForeignKey("shopify_stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    source = db.Column(String(32), nullable=False, default="workspace")
    event_type = db.Column(String(64), nullable=False, default="manual_edit")

    before_payload = db.Column(JSON, nullable=True)
    after_payload = db.Column(JSON, nullable=True)
    diff_payload = db.Column(JSON, nullable=True)
    
    # metadata_json: Stores transient event state and Phase 17 Live Reconcile anchors:
    # - shopify_version_hash: Hash of the Shopify payload at event time
    # - shopify_updated_at: Shopify's updated_at timestamp at event time
    # - dry_run_id: Associated dry-run for traceablity
    metadata_json = db.Column(JSON, nullable=True)
    
    note = db.Column(Text, nullable=True)

    resolution_batch_id = db.Column(
        Integer,
        ForeignKey("resolution_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resolution_rule_id = db.Column(
        Integer,
        ForeignKey("resolution_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    product = relationship("Product", backref="change_events")
    store = relationship("ShopifyStore")
    actor = relationship("User", foreign_keys=[actor_user_id])
    resolution_batch = relationship("ResolutionBatch")
    resolution_rule = relationship("ResolutionRule")

    def __repr__(self) -> str:
        return (
            f"<ProductChangeEvent id={self.id} product_id={self.product_id} "
            f"type={self.event_type} source={self.source}>"
        )
