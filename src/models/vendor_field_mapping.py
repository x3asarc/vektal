"""Versioned vendor field mappings for precision staging governance."""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
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


class VendorFieldMapping(db.Model, TimestampMixin):
    """Versioned supplier mapping contract per store + vendor + field-group."""

    __tablename__ = "vendor_field_mappings"
    __table_args__ = (
        CheckConstraint(
            "field_group IN ('images', 'text', 'pricing', 'ids')",
            name="vendor_field_mapping_field_group",
        ),
        CheckConstraint(
            "coverage_status IN ('ready', 'incomplete', 'draft')",
            name="vendor_field_mapping_coverage_status",
        ),
        CheckConstraint(
            "alt_text_policy IN ('preserve', 'approved_overwrite')",
            name="vendor_field_mapping_alt_text_policy",
        ),
        CheckConstraint(
            "policy_version >= 1",
            name="vendor_field_mapping_policy_version",
        ),
        UniqueConstraint(
            "store_id",
            "vendor_code",
            "field_group",
            "mapping_version",
            name="uq_vendor_mapping_version",
        ),
        Index("ix_vendor_mapping_store_vendor", "store_id", "vendor_code"),
        Index("ix_vendor_mapping_active", "store_id", "vendor_code", "field_group", "is_active"),
    )

    id = db.Column(Integer, primary_key=True)
    store_id = db.Column(
        Integer,
        ForeignKey("shopify_stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_code = db.Column(String(64), nullable=False, index=True)
    field_group = db.Column(String(32), nullable=False, index=True)
    mapping_version = db.Column(Integer, nullable=False, default=1)
    coverage_status = db.Column(String(32), nullable=False, default="incomplete")

    source_schema = db.Column(JSON, nullable=True)
    canonical_mapping = db.Column(JSON, nullable=False, default=dict)
    required_fields = db.Column(JSON, nullable=False, default=list)
    protected_columns_json = db.Column(JSON, nullable=False, default=list)
    alt_text_policy = db.Column(String(32), nullable=False, default="preserve")
    policy_version = db.Column(Integer, nullable=False, default=1)
    governance_metadata_json = db.Column(JSON, nullable=True)
    metadata_json = db.Column(JSON, nullable=True)

    is_active = db.Column(Boolean, nullable=False, default=True)
    created_by_user_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    store = relationship("ShopifyStore", backref="vendor_field_mappings")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    def __repr__(self) -> str:
        return (
            f"<VendorFieldMapping id={self.id} store_id={self.store_id} "
            f"vendor={self.vendor_code} group={self.field_group} version={self.mapping_version}>"
        )
