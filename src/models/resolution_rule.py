"""Resolution rule model for supplier + field-group policy governance."""
from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class ResolutionRule(db.Model, TimestampMixin):
    """User-governed resolution behavior, including exclusions."""

    __tablename__ = "resolution_rules"
    __table_args__ = (
        CheckConstraint(
            "field_group IN ('images', 'text', 'pricing', 'ids')",
            name="resolution_rule_field_group",
        ),
        CheckConstraint(
            "rule_type IN ('auto_apply', 'exclude', 'variant_create', 'quiz_default')",
            name="resolution_rule_type",
        ),
        Index("ix_resolution_rule_user_supplier_group", "user_id", "supplier_code", "field_group"),
    )

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_code = db.Column(String(64), nullable=False, default="*")
    field_group = db.Column(String(32), nullable=False)
    rule_type = db.Column(String(32), nullable=False)
    action = db.Column(String(64), nullable=False, default="require_approval")
    consented = db.Column(Boolean, nullable=False, default=False)
    enabled = db.Column(Boolean, nullable=False, default=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    config = db.Column(JSON, nullable=True)
    notes = db.Column(Text, nullable=True)

    created_by_user_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    user = relationship("User", foreign_keys=[user_id], backref="resolution_rules")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    def __repr__(self) -> str:
        return (
            f"<ResolutionRule id={self.id} user_id={self.user_id} "
            f"supplier={self.supplier_code} group={self.field_group} type={self.rule_type}>"
        )

