---
phase: 15-self-healing-dynamic-scripting
plan: 11a
type: execute
wave: 5
depends_on: ["15-04"]
files_modified:
  - src/models/pending_approvals.py
  - src/api/v1/approvals.py
  - tests/api/test_approvals_api.py
autonomous: true

must_haves:
  truths:
    - "Approvals persist across conversations and sessions"
    - "Approval REST API supports create, list, approve, reject operations"
    - "Approvals expire after 72h with configurable TTL"
  artifacts:
    - path: "src/models/pending_approvals.py"
      provides: "PendingApproval ORM model"
      exports: ["PendingApproval"]
    - path: "src/api/v1/approvals.py"
      provides: "Approval REST API endpoints"
      exports: []
  key_links:
    - from: "src/api/v1/approvals.py"
      to: "src/models/pending_approvals.py"
      via: "CRUD operations on approvals"
      pattern: "PendingApproval\\.query|PendingApproval\\.create"
---

<objective>
Implement persistent approval queue backend (model + API) for autonomous fixes with confidence <0.9.

Purpose: Enable human oversight for medium-confidence fixes via REST API
Output: Working approval database model and REST API endpoints
</objective>

<execution_context>
@C:/Users/Hp/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Hp/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/15-self-healing-dynamic-scripting/15-ARCHITECTURE-LOCKED.md (Section 3: Approval System)
@.planning/phases/15-self-healing-dynamic-scripting/15-04-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Create PendingApproval database model</name>
  <files>src/models/pending_approvals.py</files>
  <action>
Implement PostgreSQL schema from 15-ARCHITECTURE-LOCKED.md Section 3:

```python
from sqlalchemy import Column, Integer, String, Text, Numeric, TIMESTAMP, JSON, Index, Enum as SQLEnum
from sqlalchemy.sql import func
from src.models import db
import enum

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
    approval_id = Column(String(36), unique=True, nullable=False)
    type = Column(String(50), nullable=False)  # 'code_change', 'config_change', 'optimization'
    title = Column(String(255), nullable=False)
    description = Column(Text)
    diff = Column(Text)  # Git diff output
    confidence = Column(Numeric(3, 2), nullable=False)
    sandbox_run_id = Column(Integer)
    blast_radius_files = Column(Integer, default=0)
    blast_radius_loc = Column(Integer, default=0)

    # Workflow state
    status = Column(SQLEnum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    priority = Column(SQLEnum(ApprovalPriority), nullable=False, default=ApprovalPriority.NORMAL)

    # Timestamps
    created_at = Column(TIMESTAMP, server_default=func.now())
    expires_at = Column(TIMESTAMP)
    resolved_at = Column(TIMESTAMP)
    resolved_by_user_id = Column(Integer)
    resolution_note = Column(Text)

    # Metadata
    metadata = Column(JSON)

    __table_args__ = (
        Index('idx_pending_approvals_status', 'status', postgresql_where=(status == ApprovalStatus.PENDING)),
        Index('idx_pending_approvals_expires', 'expires_at', postgresql_where=(status == ApprovalStatus.PENDING)),
        Index('idx_pending_approvals_priority', 'priority', 'created_at'),
    )

    @classmethod
    def create_approval(cls, **kwargs):
        """Create new approval with expiration."""
        from datetime import datetime, timedelta
        import uuid

        approval = cls(
            approval_id=str(uuid.uuid4()),
            expires_at=datetime.now() + timedelta(hours=kwargs.pop('expires_in_hours', 72)),
            **kwargs
        )
        db.session.add(approval)
        db.session.commit()
        return approval

    def approve(self, user_id: int, note: str = None):
        """Mark as approved."""
        self.status = ApprovalStatus.APPROVED
        self.resolved_at = func.now()
        self.resolved_by_user_id = user_id
        self.resolution_note = note
        db.session.commit()

    def reject(self, user_id: int, note: str = None):
        """Mark as rejected."""
        self.status = ApprovalStatus.REJECTED
        self.resolved_at = func.now()
        self.resolved_by_user_id = user_id
        self.resolution_note = note
        db.session.commit()
```
  </action>
  <verify>
```bash
flask db migrate -m "Add pending_approvals table"
flask db upgrade

python -c "
from src.models.pending_approvals import PendingApproval
print('Columns:', [c.name for c in PendingApproval.__table__.columns])
assert 'approval_id' in [c.name for c in PendingApproval.__table__.columns]
print('✓ PendingApproval schema valid')
"
```
  </verify>
  <done>PendingApproval model persists approvals with expiration and workflow state</done>
</task>

<task type="auto">
  <name>Create approval REST API endpoints</name>
  <files>src/api/v1/approvals.py</files>
  <action>
REST API for approval CRUD:

```python
from flask import Blueprint, request, jsonify
from src.models.pending_approvals import PendingApproval, ApprovalStatus
from flask_login import current_user, login_required

approvals_bp = Blueprint('approvals', __name__, url_prefix='/api/v1/approvals')

@approvals_bp.route('/', methods=['GET'])
@login_required
def list_approvals():
    """List pending approvals."""
    status = request.args.get('status', 'pending')
    approvals = PendingApproval.query.filter_by(status=ApprovalStatus[status.upper()]).all()

    return jsonify({
        'approvals': [
            {
                'approval_id': a.approval_id,
                'type': a.type,
                'title': a.title,
                'confidence': float(a.confidence),
                'blast_radius_files': a.blast_radius_files,
                'created_at': a.created_at.isoformat(),
                'expires_at': a.expires_at.isoformat() if a.expires_at else None
            }
            for a in approvals
        ]
    })

@approvals_bp.route('/<approval_id>', methods=['GET'])
@login_required
def get_approval(approval_id):
    """Get approval details including diff."""
    approval = PendingApproval.query.filter_by(approval_id=approval_id).first_or_404()

    return jsonify({
        'approval_id': approval.approval_id,
        'type': approval.type,
        'title': approval.title,
        'description': approval.description,
        'diff': approval.diff,
        'confidence': float(approval.confidence),
        'sandbox_run_id': approval.sandbox_run_id,
        'status': approval.status.value,
        'created_at': approval.created_at.isoformat()
    })

@approvals_bp.route('/<approval_id>/approve', methods=['POST'])
@login_required
def approve(approval_id):
    """Approve a pending approval."""
    approval = PendingApproval.query.filter_by(approval_id=approval_id).first_or_404()
    note = request.json.get('note')

    approval.approve(user_id=current_user.id, note=note)

    return jsonify({'status': 'approved', 'approval_id': approval_id})

@approvals_bp.route('/<approval_id>/reject', methods=['POST'])
@login_required
def reject(approval_id):
    """Reject a pending approval."""
    approval = PendingApproval.query.filter_by(approval_id=approval_id).first_or_404()
    note = request.json.get('note')

    approval.reject(user_id=current_user.id, note=note)

    return jsonify({'status': 'rejected', 'approval_id': approval_id})
```

**Register blueprint in src/api/app.py:**
```python
from src.api.v1.approvals import approvals_bp
app.register_blueprint(approvals_bp)
```
  </action>
  <verify>
```bash
# Test API endpoints
curl -X GET http://localhost:5000/api/v1/approvals
```
  </verify>
  <done>REST API provides list, get, approve, reject endpoints</done>
</task>

<task type="auto">
  <name>Create approval API tests</name>
  <files>tests/api/test_approvals_api.py</files>
  <action>
Test all approval API endpoints:

**Coverage:**
1. GET /api/v1/approvals - List pending approvals
2. GET /api/v1/approvals/<id> - Get approval details
3. POST /api/v1/approvals/<id>/approve - Approve
4. POST /api/v1/approvals/<id>/reject - Reject
5. Expiration logic (auto-reject after 72h)
6. Pagination and filtering

**Test Cases:**
```python
import pytest
from src.models.pending_approvals import PendingApproval, ApprovalStatus

def test_list_approvals(client):
    """Test listing pending approvals."""
    approval = PendingApproval.create_approval(
        type='code_change',
        title='Test approval',
        description='Test',
        diff='...',
        confidence=0.85
    )

    response = client.get('/api/v1/approvals')
    assert response.status_code == 200
    assert len(response.json['approvals']) == 1
    assert response.json['approvals'][0]['approval_id'] == approval.approval_id

def test_get_approval_details(client):
    """Test getting approval details."""
    approval = PendingApproval.create_approval(
        type='code_change',
        title='Test approval',
        description='Test description',
        diff='diff content',
        confidence=0.85
    )

    response = client.get(f'/api/v1/approvals/{approval.approval_id}')
    assert response.status_code == 200
    assert response.json['diff'] == 'diff content'

def test_approve_approval(client):
    """Test approving a pending approval."""
    approval = PendingApproval.create_approval(
        type='code_change',
        title='Test approval',
        description='Test',
        diff='...',
        confidence=0.85
    )

    response = client.post(f'/api/v1/approvals/{approval.approval_id}/approve')
    assert response.status_code == 200

    # Verify status updated
    from src.models import db
    db.session.refresh(approval)
    assert approval.status == ApprovalStatus.APPROVED

def test_reject_approval(client):
    """Test rejecting a pending approval."""
    approval = PendingApproval.create_approval(
        type='code_change',
        title='Test approval',
        description='Test',
        diff='...',
        confidence=0.85
    )

    response = client.post(
        f'/api/v1/approvals/{approval.approval_id}/reject',
        json={'note': 'Not ready'}
    )
    assert response.status_code == 200

    from src.models import db
    db.session.refresh(approval)
    assert approval.status == ApprovalStatus.REJECTED
    assert approval.resolution_note == 'Not ready'
```
  </action>
  <verify>
```bash
python -m pytest tests/api/test_approvals_api.py -v
```
  </verify>
  <done>API tests validate all approval endpoints and workflow state transitions</done>
</task>

</tasks>

<verification>
- PendingApproval model persists to PostgreSQL with indexes
- REST API provides list, get, approve, reject operations
- All endpoints require authentication
- Tests validate CRUD operations and state transitions
</verification>

<success_criteria>
1. PendingApproval model persists approvals with status, priority, expiration
2. REST API provides list, get, approve, reject endpoints
3. All endpoints authenticated with Flask-Login
4. Database migrations apply cleanly
5. Test suite validates all API endpoints
6. Approvals queryable by status and sorted by priority
</success_criteria>

<output>
After completion, create `.planning/phases/15-self-healing-dynamic-scripting/15-11a-SUMMARY.md`
</output>
