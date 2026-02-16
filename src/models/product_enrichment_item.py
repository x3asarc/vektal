"""Per-product/per-field enrichment decision lineage."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, Numeric, String
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class ProductEnrichmentItem(db.Model, TimestampMixin):
    """Item-level enrichment recommendation + policy decision state."""

    __tablename__ = "product_enrichment_items"
    __table_args__ = (
        CheckConstraint(
            "field_group IN ('images', 'text', 'pricing', 'ids', 'metadata')",
            name="product_enrichment_item_field_group",
        ),
        CheckConstraint(
            "decision_state IN ('suggested', 'blocked', 'approved', 'rejected', 'applied')",
            name="product_enrichment_item_decision_state",
        ),
        Index("ix_product_enrichment_item_run_state", "run_id", "decision_state"),
        Index("ix_product_enrichment_item_product", "product_id"),
    )

    id = db.Column(Integer, primary_key=True)
    run_id = db.Column(
        Integer,
        ForeignKey("product_enrichment_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = db.Column(
        Integer,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    field_group = db.Column(String(32), nullable=False)
    field_name = db.Column(String(128), nullable=False, index=True)
    decision_state = db.Column(String(32), nullable=False, default="suggested")

    before_value = db.Column(JSON, nullable=True)
    after_value = db.Column(JSON, nullable=True)
    confidence = db.Column(Numeric(4, 3), nullable=True)
    provenance = db.Column(JSON, nullable=True)
    reason_codes = db.Column(JSON, nullable=False, default=list)
    evidence_refs = db.Column(JSON, nullable=True)

    requires_user_action = db.Column(db.Boolean, nullable=False, default=True)
    is_protected_column = db.Column(db.Boolean, nullable=False, default=False)
    alt_text_preserved = db.Column(db.Boolean, nullable=False, default=True)

    policy_version = db.Column(Integer, nullable=False, default=1)
    mapping_version = db.Column(Integer, nullable=True)
    metadata_json = db.Column(JSON, nullable=True)

    run = relationship("ProductEnrichmentRun", back_populates="items")
    product = relationship("Product", back_populates="enrichment_items")

    def __repr__(self) -> str:
        return (
            f"<ProductEnrichmentItem id={self.id} run_id={self.run_id} "
            f"field={self.field_name} state={self.decision_state}>"
        )
