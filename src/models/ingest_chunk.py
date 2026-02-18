"""Ingest chunk persistence model for Phase 6 orchestration."""
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


class IngestChunkStatus(enum.Enum):
    """Chunk state machine."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED_TERMINAL = "failed_terminal"


class IngestChunk(db.Model, TimestampMixin):
    """Chunk claim/reclaim and completion state."""

    __tablename__ = "ingest_chunks"
    __table_args__ = (
        UniqueConstraint("job_id", "chunk_idx", name="uq_ingest_chunks_job_chunk_idx"),
        CheckConstraint(
            "processed_expected >= 0 "
            "AND processed_actual >= 0 "
            "AND processed_actual <= processed_expected",
            name="ck_ingest_chunks_processed_bounds",
        ),
        CheckConstraint(
            "status != 'COMPLETED' OR completed_at IS NOT NULL",
            name="ck_ingest_chunks_completed_has_timestamp",
        ),
    )

    id = db.Column(Integer, primary_key=True)
    job_id = db.Column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    store_id = db.Column(Integer, nullable=False, index=True)
    chunk_idx = db.Column(Integer, nullable=False)

    status = db.Column(
        SQLEnum(IngestChunkStatus, name="ingest_chunk_status", create_constraint=True),
        default=IngestChunkStatus.PENDING,
        nullable=False,
        index=True,
    )

    claim_token = db.Column(String(64), nullable=True, index=True)
    claimed_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    attempts = db.Column(Integer, default=0, nullable=False)

    processed_expected = db.Column(Integer, default=0, nullable=False)
    processed_actual = db.Column(Integer, default=0, nullable=False)
    product_ids_json = db.Column(JSON, nullable=False, default=list)

    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_error = db.Column(Text, nullable=True)
    task_id = db.Column(String(255), nullable=True)
    cancellation_code = db.Column(String(64), nullable=True)

    job = relationship("Job", back_populates="ingest_chunks")

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            IngestChunkStatus.COMPLETED,
            IngestChunkStatus.FAILED_TERMINAL,
        }

    def __repr__(self) -> str:
        return (
            f"<IngestChunk job_id={self.job_id} idx={self.chunk_idx} "
            f"status={self.status.value}>"
        )

