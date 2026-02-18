"""Runtime reliability policy and breaker state persistence."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


def _default_retry_policy() -> dict:
    return {
        "rate_limit": {"max_retries": 3, "strategy": "exponential_jitter"},
        "server_error": {"max_retries": 2, "strategy": "linear"},
        "timeout": {"max_retries": 1, "strategy": "timeout_multiplier"},
        "connectivity": {"max_retries": 3, "strategy": "immediate"},
        "schema_validation": {"max_retries": 1, "strategy": "reflexive_fixer"},
    }


class AssistantRuntimePolicy(db.Model, TimestampMixin):
    """Versioned reliability policy object for skill/provider execution paths."""

    __tablename__ = "assistant_runtime_policies"
    __table_args__ = (
        CheckConstraint(
            "scope_kind IN ('global', 'provider', 'skill', 'provider_skill')",
            name="assistant_runtime_policy_scope_kind",
        ),
        CheckConstraint(
            "breaker_state IN ('closed', 'open', 'half_open')",
            name="assistant_runtime_policy_breaker_state",
        ),
        CheckConstraint(
            "breaker_error_rate_threshold > 0 AND breaker_error_rate_threshold <= 1",
            name="assistant_runtime_policy_error_rate_threshold",
        ),
        CheckConstraint(
            "breaker_min_sample_size >= 1",
            name="assistant_runtime_policy_min_sample_size",
        ),
        CheckConstraint(
            "breaker_open_cooldown_seconds >= 1",
            name="assistant_runtime_policy_open_cooldown",
        ),
        UniqueConstraint(
            "scope_kind",
            "provider_name",
            "skill_name",
            "policy_version",
            name="uq_assistant_runtime_policy_scope_version",
        ),
        Index("ix_assistant_runtime_policy_active_effective", "is_active", "effective_at"),
        Index("ix_assistant_runtime_policy_scope", "scope_kind", "provider_name", "skill_name"),
    )

    id = db.Column(Integer, primary_key=True)
    scope_kind = db.Column(String(32), nullable=False, default="global")
    provider_name = db.Column(String(64), nullable=True, index=True)
    skill_name = db.Column(String(96), nullable=True, index=True)
    policy_version = db.Column(Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    effective_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    changed_by_id = db.Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    breaker_state = db.Column(String(16), nullable=False, default="closed")
    breaker_error_count = db.Column(Integer, nullable=False, default=0)
    breaker_request_count = db.Column(Integer, nullable=False, default=0)
    breaker_consecutive_successes = db.Column(Integer, nullable=False, default=0)
    breaker_last_failure_at = db.Column(db.DateTime(timezone=True), nullable=True)
    breaker_last_success_at = db.Column(db.DateTime(timezone=True), nullable=True)
    breaker_opened_at = db.Column(db.DateTime(timezone=True), nullable=True)

    breaker_error_rate_threshold = db.Column(db.Float, nullable=False, default=0.25)
    breaker_latency_p95_tier12_seconds = db.Column(db.Float, nullable=False, default=15.0)
    breaker_latency_p95_tier3_seconds = db.Column(db.Float, nullable=False, default=45.0)
    breaker_window_seconds = db.Column(Integer, nullable=False, default=300)
    breaker_min_sample_size = db.Column(Integer, nullable=False, default=10)
    breaker_open_cooldown_seconds = db.Column(Integer, nullable=False, default=60)
    breaker_half_open_successes = db.Column(Integer, nullable=False, default=3)

    retry_policy_json = db.Column(JSON, nullable=False, default=_default_retry_policy)
    metadata_json = db.Column(JSON, nullable=True)

    changed_by = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<AssistantRuntimePolicy id={self.id} scope={self.scope_kind} "
            f"provider={self.provider_name} skill={self.skill_name} v={self.policy_version}>"
        )

