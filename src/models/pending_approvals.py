from src.models import db
import enum
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import Column, Integer, String, Text, Numeric, TIMESTAMP, JSON, Index, Enum as SQLEnum
from sqlalchemy.sql import func

class ApprovalStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class ApprovalPriority(enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class PendingApproval(db.Model):
    __tablename__ = 'pending_approvals'

    id = Column(Integer, primary_key=True)
    approval_id = Column(String(36), unique=True, nullable=False, index=True)
    type = Column(String(50), nullable=False)  # 'code_change', 'config_change', 'optimization'
    title = Column(String(255), nullable=False)
    description = Column(Text)
    diff = Column(Text)  # Git diff output
    confidence = Column(Numeric(3, 2), nullable=False)
    sandbox_run_id = Column(String(36)) # Reference to SandboxRun.run_id
    blast_radius_files = Column(Integer, default=0)
    blast_radius_loc = Column(Integer, default=0)

    # Workflow state
    status = Column(SQLEnum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    priority = Column(SQLEnum(ApprovalPriority), nullable=False, default=ApprovalPriority.NORMAL)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    resolved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    resolved_by_user_id = Column(Integer, nullable=True)
    resolution_note = Column(Text, nullable=True)

    # Metadata
    metadata_json = Column(JSON, nullable=True)

    __table_args__ = (
        Index('idx_pending_approvals_status', 'status'),
        Index('idx_pending_approvals_expires', 'expires_at'),
        Index('idx_pending_approvals_priority', 'priority', 'created_at'),
    )

    @classmethod
    def create_approval(cls, **kwargs):
        """Create new approval with expiration."""
        expires_in_hours = kwargs.pop('expires_in_hours', 72)
        approval = cls(
            approval_id=str(uuid.uuid4()),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
            **kwargs
        )
        db.session.add(approval)
        db.session.commit()
        return approval

    def approve(self, user_id: int, note: str = None):
        """Mark as approved."""
        self.status = ApprovalStatus.APPROVED
        self.resolved_at = datetime.now(timezone.utc)
        self.resolved_by_user_id = user_id
        self.resolution_note = note
        db.session.add(self)
        db.session.commit()

    def reject(self, user_id: int, note: str = None):
        """Mark as rejected."""
        self.status = ApprovalStatus.REJECTED
        self.resolved_at = datetime.now(timezone.utc)
        self.resolved_by_user_id = user_id
        self.resolution_note = note
        db.session.add(self)
        db.session.commit()
