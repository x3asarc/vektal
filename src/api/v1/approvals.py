from flask import Blueprint, request, jsonify, abort
from src.models.pending_approvals import PendingApproval, ApprovalStatus
from src.models import db
from flask_login import current_user, login_required
import logging

logger = logging.getLogger(__name__)

approvals_bp = Blueprint('approvals', __name__, url_prefix='/api/v1/approvals')

@approvals_bp.route('/', methods=['GET'])
@login_required
def list_approvals():
    """List pending approvals."""
    status_str = request.args.get('status', 'pending').upper()
    try:
        status = ApprovalStatus[status_str]
    except KeyError:
        return jsonify({'error': f'Invalid status: {status_str}'}), 400

    approvals = PendingApproval.query.filter_by(status=status).order_by(PendingApproval.created_at.desc()).all()

    return jsonify({
        'approvals': [
            {
                'approval_id': a.approval_id,
                'type': a.type,
                'title': a.title,
                'confidence': float(a.confidence),
                'blast_radius_files': a.blast_radius_files,
                'status': a.status.value,
                'priority': a.priority.value,
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
        'priority': approval.priority.value,
        'created_at': approval.created_at.isoformat(),
        'expires_at': approval.expires_at.isoformat() if approval.expires_at else None,
        'metadata': approval.metadata_json
    })

@approvals_bp.route('/<approval_id>/approve', methods=['POST'])
@login_required
def approve(approval_id):
    """Approve a pending approval."""
    approval = PendingApproval.query.filter_by(approval_id=approval_id).first_or_404()
    if approval.status != ApprovalStatus.PENDING:
        return jsonify({'error': 'Approval is not in pending state'}), 400

    note = request.json.get('note') if request.is_json else None

    try:
        approval.approve(user_id=current_user.id, note=note)
        logger.info(f"Approval {approval_id} APPROVED by user {current_user.id}")
        return jsonify({'status': 'approved', 'approval_id': approval_id})
    except Exception as e:
        logger.error(f"Failed to approve {approval_id}: {e}")
        return jsonify({'error': str(e)}), 500

@approvals_bp.route('/<approval_id>/reject', methods=['POST'])
@login_required
def reject(approval_id):
    """Reject a pending approval."""
    approval = PendingApproval.query.filter_by(approval_id=approval_id).first_or_404()
    if approval.status != ApprovalStatus.PENDING:
        return jsonify({'error': 'Approval is not in pending state'}), 400

    note = request.json.get('note') if request.is_json else None

    try:
        approval.reject(user_id=current_user.id, note=note)
        logger.info(f"Approval {approval_id} REJECTED by user {current_user.id}")
        return jsonify({'status': 'rejected', 'approval_id': approval_id})
    except Exception as e:
        logger.error(f"Failed to reject {approval_id}: {e}")
        return jsonify({'error': str(e)}), 500
