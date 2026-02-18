"""
Background job models and execution guardrails.

Phase 6 keeps legacy fields for API compatibility while introducing
DB-authoritative orchestration fields.
"""
import enum

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Enum as SQLEnum,
    text,
)
from sqlalchemy.orm import relationship

from src.models import TimestampMixin, db


class JobStatus(enum.Enum):
    """Job execution status."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    COMPLETED = "completed"
    FAILED = "failed"
    FAILED_TERMINAL = "failed_terminal"
    CANCELLED = "cancelled"


class JobType(enum.Enum):
    """Types of background jobs."""

    PRODUCT_SYNC = "product_sync"
    PRODUCT_ENRICH = "product_enrich"
    IMAGE_PROCESS = "image_process"
    CATALOG_IMPORT = "catalog_import"
    VENDOR_SCRAPE = "vendor_scrape"
    INGEST_CATALOG = "ingest_catalog"


class Job(db.Model, TimestampMixin):
    """
    Background job tracking for Celery tasks.

    DB fields `total_products` and `processed_count` are the Phase 6 source
    of truth. Legacy fields are mirrored to preserve existing API contracts.
    """

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "processed_count >= 0 AND processed_count <= total_products",
            name="job_processed_count_bounds",
        ),
        CheckConstraint(
            "processed_items >= 0 AND processed_items <= total_items",
            name="job_processed_items_bounds",
        ),
        Index(
            "uq_jobs_active_ingest_per_store",
            "store_id",
            unique=True,
            postgresql_where=text(
                "store_id IS NOT NULL "
                "AND job_type = 'INGEST_CATALOG' "
                "AND status IN ('PENDING', 'QUEUED', 'RUNNING', 'CANCEL_REQUESTED')"
            ),
        ),
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
        nullable=True,
        index=True,
    )

    # Celery task tracking
    celery_task_id = db.Column(String(255), unique=True, index=True)

    # Job identification
    job_type = db.Column(
        SQLEnum(JobType, name="job_type", create_constraint=True),
        nullable=False,
        index=True,
    )
    job_name = db.Column(String(255))

    status = db.Column(
        SQLEnum(JobStatus, name="job_status", create_constraint=True),
        default=JobStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Phase 6 canonical counters
    total_products = db.Column(Integer, default=0, nullable=False)
    processed_count = db.Column(Integer, default=0, nullable=False)

    # Legacy counters (kept for compatibility with existing API/frontend)
    total_items = db.Column(Integer, default=0, nullable=False)
    processed_items = db.Column(Integer, default=0, nullable=False)
    successful_items = db.Column(Integer, default=0, nullable=False)
    failed_items = db.Column(Integer, default=0, nullable=False)

    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))
    cancellation_requested_at = db.Column(db.DateTime(timezone=True))

    error_message = db.Column(Text)
    error_traceback = db.Column(Text)
    terminal_reason = db.Column(String(255))
    parameters = db.Column(JSON)

    user = relationship("User", back_populates="jobs")
    store = relationship("ShopifyStore", backref="jobs")

    results = relationship(
        "JobResult",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="JobResult.created_at",
    )
    ingest_chunks = relationship(
        "IngestChunk",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="IngestChunk.chunk_idx",
    )
    audit_checkpoints = relationship(
        "AuditCheckpoint",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="AuditCheckpoint.checkpoint",
    )

    @property
    def progress_percent(self) -> float:
        """Calculate progress using canonical fields."""
        if self.total_products <= 0:
            return 0.0
        return round((self.processed_count / self.total_products) * 100, 2)

    @property
    def is_terminal(self) -> bool:
        """Whether this job reached a terminal state."""
        return self.status in {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.FAILED_TERMINAL,
            JobStatus.CANCELLED,
        }

    def set_progress(self, processed: int, total: int | None = None) -> None:
        """Update canonical counters and mirror legacy fields."""
        if total is not None:
            self.total_products = max(total, 0)
            self.total_items = self.total_products
        self.processed_count = max(processed, 0)
        self.processed_items = self.processed_count

    def __repr__(self):
        return (
            f"<Job {self.job_type.value} store_id={self.store_id} "
            f"status={self.status.value}>"
        )


class JobResult(db.Model, TimestampMixin):
    """
    Per-item results for bulk job operations.

    Tracks success/failure for each item processed in a job.
    """

    __tablename__ = "job_results"

    id = db.Column(Integer, primary_key=True)
    job_id = db.Column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    item_sku = db.Column(String(255), index=True)
    item_barcode = db.Column(String(255))
    item_identifier = db.Column(String(255))

    status = db.Column(String(50), nullable=False)
    product_id = db.Column(Integer, ForeignKey("products.id", ondelete="SET NULL"))

    error_message = db.Column(Text)
    needs_review = db.Column(db.Boolean, default=False)
    review_reason = db.Column(String(255))
    result_data = db.Column(JSON)

    job = relationship("Job", back_populates="results")

    def __repr__(self):
        return (
            f"<JobResult job_id={self.job_id} "
            f"identifier={self.item_identifier} status={self.status}>"
        )
