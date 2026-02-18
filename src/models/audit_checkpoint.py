"""Audit checkpoint outbox model for durable dispatch."""
import enum

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class AuditDispatchStatus(enum.Enum):
    """Outbox dispatch states."""

    PENDING_DISPATCH = "pending_dispatch"
    DISPATCHED = "dispatched"


class AuditCheckpoint(db.Model, TimestampMixin):
    """Durable checkpoint intents that are published by dispatcher workers."""

    __tablename__ = "audit_checkpoints"
    __table_args__ = (
        UniqueConstraint("job_id", "checkpoint", name="uq_audit_checkpoints_job_checkpoint"),
        CheckConstraint("checkpoint >= 1 AND checkpoint <= 100", name="ck_audit_checkpoint_bounds"),
    )

    id = db.Column(Integer, primary_key=True)
    job_id = db.Column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    store_id = db.Column(Integer, nullable=False, index=True)
    checkpoint = db.Column(Integer, nullable=False)

    dispatch_status = db.Column(
        SQLEnum(AuditDispatchStatus, name="audit_dispatch_status", create_constraint=True),
        default=AuditDispatchStatus.PENDING_DISPATCH,
        nullable=False,
        index=True,
    )
    dispatch_attempts = db.Column(Integer, default=0, nullable=False)
    next_dispatch_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    dispatched_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_error = db.Column(Text, nullable=True)
    payload = db.Column(JSON, nullable=True)
    task_id = db.Column(String(255), nullable=True)

    job = relationship("Job", back_populates="audit_checkpoints")

    def __repr__(self) -> str:
        return (
            f"<AuditCheckpoint job_id={self.job_id} "
            f"checkpoint={self.checkpoint} status={self.dispatch_status.value}>"
        )

