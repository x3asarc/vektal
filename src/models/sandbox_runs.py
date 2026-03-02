"""Sandbox run persistence model for Phase 15 verification workflow."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index

from src.models import db


class SandboxVerdict(enum.Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class SandboxRun(db.Model):
    __tablename__ = "sandbox_runs"
    __table_args__ = (
        Index("idx_sandbox_runs_verdict", "verdict"),
        Index("idx_sandbox_runs_fingerprint", "failure_fingerprint"),
    )

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.String(36), unique=True, nullable=False, index=True)

    failure_fingerprint = db.Column(db.String(255), nullable=True)
    remediation_type = db.Column(db.String(50), nullable=True)

    changed_files = db.Column(db.JSON, nullable=False)
    blast_radius_files = db.Column(db.Integer, nullable=False, default=0)
    blast_radius_loc = db.Column(db.Integer, nullable=False, default=0)

    verdict = db.Column(SQLEnum(SandboxVerdict), nullable=False)
    gate_results = db.Column(db.JSON, nullable=True)
    confidence = db.Column(db.Numeric(3, 2), nullable=True)

    duration_ms = db.Column(db.Integer, nullable=True)
    container_id = db.Column(db.String(64), nullable=True)
    logs = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    rollback_notes = db.Column(db.Text, nullable=True)
