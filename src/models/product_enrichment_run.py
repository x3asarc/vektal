"""Durable enrichment run lifecycle and policy lineage contracts."""
from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class ProductEnrichmentRun(db.Model, TimestampMixin):
    """Run-level enrichment metadata and dry-run lifecycle persistence."""

    __tablename__ = "product_enrichment_runs"
    __table_args__ = (
        CheckConstraint(
            "run_profile IN ('quick', 'standard', 'deep')",
            name="product_enrichment_run_profile",
        ),
        CheckConstraint(
            "status IN ('draft', 'dry_run_ready', 'approved', 'applied', 'expired', 'cancelled')",
            name="product_enrichment_run_status",
        ),
        CheckConstraint(
            "target_language IN ('de', 'en')",
            name="product_enrichment_run_language",
        ),
        CheckConstraint(
            "alt_text_policy IN ('preserve', 'approved_overwrite')",
            name="product_enrichment_run_alt_text_policy",
        ),
        UniqueConstraint(
            "store_id",
            "idempotency_hash",
            name="uq_product_enrichment_run_store_hash",
        ),
        Index("ix_product_enrichment_run_store_status", "store_id", "status"),
        Index("ix_product_enrichment_run_user_status", "user_id", "status"),
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
        ForeignKey("shopify_stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_code = db.Column(String(64), nullable=False, index=True)

    run_profile = db.Column(String(32), nullable=False, default="quick")
    target_language = db.Column(String(8), nullable=False, default="de")
    status = db.Column(String(32), nullable=False, default="draft", index=True)

    policy_version = db.Column(Integer, nullable=False, default=1)
    mapping_version = db.Column(Integer, nullable=True)
    idempotency_hash = db.Column(String(64), nullable=False, index=True)

    dry_run_expires_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    alt_text_policy = db.Column(String(32), nullable=False, default="preserve")
    protected_columns_json = db.Column(JSON, nullable=False, default=list)

    capability_audit_json = db.Column(JSON, nullable=True)
    metadata_json = db.Column(JSON, nullable=True)

    user = relationship("User", backref="product_enrichment_runs")
    store = relationship("ShopifyStore", backref="product_enrichment_runs")
    items = relationship(
        "ProductEnrichmentItem",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="ProductEnrichmentItem.id",
    )

    def __repr__(self) -> str:
        return (
            f"<ProductEnrichmentRun id={self.id} store_id={self.store_id} "
            f"vendor={self.vendor_code} status={self.status}>"
        )
