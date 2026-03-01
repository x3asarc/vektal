"""Canonical assistant tool registry for tier and policy projection."""
from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, JSON, String, Text

from src.models import TimestampMixin, db


class AssistantToolRegistry(db.Model, TimestampMixin):
    """System tool capability metadata used for runtime projection."""

    __tablename__ = "assistant_tool_registry"
    __table_args__ = (
        CheckConstraint(
            "risk_class IN ('low', 'medium', 'high', 'critical')",
            name="assistant_tool_registry_risk_class",
        ),
        Index("ix_assistant_tool_registry_enabled", "enabled"),
    )

    id = db.Column(Integer, primary_key=True)
    tool_id = db.Column(String(96), nullable=False, unique=True, index=True)
    display_name = db.Column(String(128), nullable=False)
    description = db.Column(Text, nullable=True)
    risk_class = db.Column(String(16), nullable=False, default="low")
    mutates_data = db.Column(Boolean, nullable=False, default=False)
    requires_integration = db.Column(String(64), nullable=True, index=True)
    allowed_tiers = db.Column(
        JSON,
        nullable=False,
        default=lambda: ["tier_1", "tier_2", "tier_3"],
    )
    required_role = db.Column(String(64), nullable=True)
    enabled = db.Column(Boolean, nullable=False, default=True)
    metadata_json = db.Column(JSON, nullable=True)
    schema_json = db.Column(JSON, nullable=False, server_default='{}')

    def to_tool_schema(self) -> dict:
        """Return full tool schema for MCP interface."""
        return self.schema_json if isinstance(self.schema_json, dict) else {}

    def __repr__(self) -> str:
        return f"<AssistantToolRegistry tool_id={self.tool_id} risk={self.risk_class}>"

