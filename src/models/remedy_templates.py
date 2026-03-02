"""Remedy template cache model for session-memory priming."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Index

from src.models import db


class RemedyTemplate(db.Model):
    """
    PostgreSQL cache for frequently-used remedy templates.

    Source of truth remains Neo4j/graph memory.
    This table optimizes low-latency lookup for session primer injection.
    """

    __tablename__ = "remedy_template_cache"
    __table_args__ = (
        Index("idx_remedy_fingerprint_conf", "fingerprint", "confidence"),
        Index("idx_remedy_last_applied", "last_applied_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.String(36), unique=True, nullable=False, index=True)

    fingerprint = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    remedy_payload = db.Column(db.Text, nullable=True)

    confidence = db.Column(db.Numeric(3, 2), nullable=False)
    application_count = db.Column(db.Integer, nullable=False, default=0)
    success_count = db.Column(db.Integer, nullable=False, default=0)

    affected_files_json = db.Column(db.JSON, nullable=True)
    source_commit_sha = db.Column(db.String(40), nullable=True)

    last_applied_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cache_refreshed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @classmethod
    def query_relevant(cls, failure_context: str, limit: int = 5) -> list["RemedyTemplate"]:
        """Return relevant templates from cache."""
        if not failure_context:
            return []

        now = datetime.now(timezone.utc)
        recent_threshold = now - timedelta(days=30)

        return (
            cls.query.filter(
                cls.fingerprint.contains(failure_context),
                cls.confidence >= 0.70,
                db.or_(cls.expires_at.is_(None), cls.expires_at > now),
                db.or_(cls.last_applied_at.is_(None), cls.last_applied_at >= recent_threshold),
            )
            .order_by(cls.application_count.desc(), cls.confidence.desc())
            .limit(max(1, int(limit)))
            .all()
        )

    @classmethod
    def from_graph_result(cls, record: dict[str, Any]) -> "RemedyTemplate":
        """Create detached instance from Neo4j result payload."""
        return cls(
            template_id=str(record.get("template_id") or record.get("id") or ""),
            fingerprint=str(record.get("fingerprint") or ""),
            description=record.get("description"),
            remedy_payload=record.get("remedy_payload"),
            confidence=record.get("confidence") or 0.0,
            application_count=int(record.get("application_count") or 0),
            success_count=int(record.get("success_count") or 0),
            affected_files_json=record.get("affected_files_json") or record.get("affected_files"),
            source_commit_sha=record.get("source_commit_sha"),
            last_applied_at=record.get("last_applied_at"),
            expires_at=record.get("expires_at"),
        )

    @classmethod
    def upsert_from_graph(cls, record: dict[str, Any]) -> "RemedyTemplate":
        """Upsert template into PostgreSQL from Neo4j record."""
        template_id = str(record.get("template_id") or record.get("id") or "")
        existing = cls.query.filter_by(template_id=template_id).first()
        
        if existing:
            existing.fingerprint = str(record.get("fingerprint") or existing.fingerprint)
            existing.description = record.get("description") or existing.description
            existing.remedy_payload = record.get("remedy_payload") or existing.remedy_payload
            existing.confidence = record.get("confidence") or existing.confidence
            existing.application_count = int(record.get("application_count") or existing.application_count)
            existing.success_count = int(record.get("success_count") or existing.success_count)
            existing.affected_files_json = record.get("affected_files_json") or record.get("affected_files") or existing.affected_files_json
            existing.last_applied_at = record.get("last_applied_at") or existing.last_applied_at
            existing.cache_refreshed_at = datetime.now(timezone.utc)
            db.session.add(existing)
            db.session.commit()
            return existing
        else:
            new_tmpl = cls.from_graph_result(record)
            db.session.add(new_tmpl)
            db.session.commit()
            return new_tmpl

    def cache_refresh(self) -> None:
        self.cache_refreshed_at = datetime.now(timezone.utc)
        db.session.add(self)
        db.session.commit()

    def mark_applied(self, success: bool = True) -> None:
        self.application_count = int(self.application_count or 0) + 1
        if success:
            self.success_count = int(self.success_count or 0) + 1
        self.last_applied_at = datetime.now(timezone.utc)
        self.cache_refreshed_at = datetime.now(timezone.utc)
        db.session.add(self)
        db.session.commit()

    def expire_if_files_changed(self, changed_files: list[str], overlap_threshold: float = 0.5) -> bool:
        """
        Expire template when affected files diverge significantly.

        Returns True when expiration occurred.
        """
        affected = [str(p) for p in (self.affected_files_json or []) if p]
        if not affected or not changed_files:
            return False

        affected_set = set(affected)
        changed_set = set(str(p) for p in changed_files if p)
        overlap = len(affected_set & changed_set)
        ratio = overlap / max(1, len(affected_set))
        if ratio >= overlap_threshold:
            self.expires_at = datetime.now(timezone.utc)
            self.cache_refreshed_at = datetime.now(timezone.utc)
            db.session.add(self)
            db.session.commit()
            return True
        return False
