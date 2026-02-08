"""
Background job tracking models.

Job: Celery task metadata and progress tracking
JobResult: Per-item results for bulk operations
"""
from sqlalchemy import String, Integer, Text, ForeignKey, BigInteger, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.models import db, TimestampMixin
import enum


class JobStatus(enum.Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(enum.Enum):
    """Types of background jobs."""
    PRODUCT_SYNC = "product_sync"
    PRODUCT_ENRICH = "product_enrich"
    IMAGE_PROCESS = "image_process"
    CATALOG_IMPORT = "catalog_import"
    VENDOR_SCRAPE = "vendor_scrape"


class Job(db.Model, TimestampMixin):
    """
    Background job tracking for Celery tasks.

    Stores job metadata, progress, and timing information.
    """
    __tablename__ = 'jobs'

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Celery task tracking
    celery_task_id = db.Column(String(255), unique=True, index=True)

    # Job identification
    job_type = db.Column(
        SQLEnum(JobType, name='job_type', create_constraint=True),
        nullable=False,
        index=True
    )
    job_name = db.Column(String(255))  # Human-readable name

    # Status
    status = db.Column(
        SQLEnum(JobStatus, name='job_status', create_constraint=True),
        default=JobStatus.PENDING,
        nullable=False,
        index=True
    )

    # Progress tracking
    total_items = db.Column(Integer, default=0)
    processed_items = db.Column(Integer, default=0)
    successful_items = db.Column(Integer, default=0)
    failed_items = db.Column(Integer, default=0)

    # Timing
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))

    # Error tracking
    error_message = db.Column(Text)
    error_traceback = db.Column(Text)

    # Job parameters (for retry/debugging)
    parameters = db.Column(JSON)

    # Relationships
    user = relationship('User', back_populates='jobs')

    results = relationship(
        'JobResult',
        back_populates='job',
        cascade='all, delete-orphan',
        lazy='dynamic',
        order_by='JobResult.created_at'
    )

    @property
    def progress_percent(self) -> float:
        """Calculate job progress percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100

    def __repr__(self):
        return f'<Job {self.job_type.value} user_id={self.user_id} status={self.status.value}>'


class JobResult(db.Model, TimestampMixin):
    """
    Per-item results for bulk job operations.

    Tracks success/failure for each item processed in a job.
    """
    __tablename__ = 'job_results'

    id = db.Column(Integer, primary_key=True)
    job_id = db.Column(
        Integer,
        ForeignKey('jobs.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Item identification
    item_sku = db.Column(String(255), index=True)
    item_barcode = db.Column(String(255))
    item_identifier = db.Column(String(255))  # Flexible identifier

    # Result
    status = db.Column(String(50), nullable=False)  # success, error, skipped
    product_id = db.Column(Integer, ForeignKey('products.id', ondelete='SET NULL'))  # Result product if created

    # Error tracking
    error_message = db.Column(Text)

    # Flags for review
    needs_review = db.Column(db.Boolean, default=False)
    review_reason = db.Column(String(255))

    # Result data (flexible JSON)
    result_data = db.Column(JSON)

    # Relationships
    job = relationship('Job', back_populates='results')

    def __repr__(self):
        return f'<JobResult job_id={self.job_id} sku={self.item_sku} status={self.status}>'
