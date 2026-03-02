#!/usr/bin/env python
import click
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.models.pending_approvals import PendingApproval, ApprovalStatus
from src.app_factory import create_app

@click.group()
def cli():
    """Approval queue management CLI."""
    pass

@cli.command()
def list():
    """List pending approvals."""
    app = create_app()
    with app.app_context():
        approvals = PendingApproval.query.filter_by(status=ApprovalStatus.PENDING).all()

        click.echo(f"PENDING APPROVALS ({len(approvals)})")
        for i, a in enumerate(approvals, 1):
            # Make a.created_at timezone-aware if it's not
            created_at = a.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
                
            age = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
            click.echo(f"\n[{i}] {a.title} (confidence: {float(a.confidence):.2f})")
            click.echo(f"    Files: {a.blast_radius_files} | LOC: {a.blast_radius_loc} | Age: {age:.1f}h")
            click.echo(f"    ID: {a.approval_id}")
            click.echo(f"    → python src/cli/approvals.py approve {a.approval_id}")

@cli.command()
@click.argument('approval_id')
@click.option('--note', default=None)
def approve(approval_id, note):
    """Approve pending approval."""
    app = create_app()
    with app.app_context():
        approval = PendingApproval.query.filter_by(approval_id=approval_id).first()
        if not approval:
            click.echo(f"ERROR: Approval {approval_id} not found")
            return

        if approval.status != ApprovalStatus.PENDING:
            click.echo(f"ERROR: Approval is already {approval.status.value}")
            return

        approval.approve(user_id=1, note=note)  # CLI user ID = 1
        click.echo(f"✓ Approved: {approval.title}")

@cli.command()
@click.argument('approval_id')
@click.option('--note', default=None)
def reject(approval_id, note):
    """Reject pending approval."""
    app = create_app()
    with app.app_context():
        approval = PendingApproval.query.filter_by(approval_id=approval_id).first()
        if not approval:
            click.echo(f"ERROR: Approval {approval_id} not found")
            return

        if approval.status != ApprovalStatus.PENDING:
            click.echo(f"ERROR: Approval is already {approval.status.value}")
            return

        approval.reject(user_id=1, note=note)
        click.echo(f"✓ Rejected: {approval.title}")

@cli.command()
@click.argument('approval_id')
def diff(approval_id):
    """View approval diff."""
    app = create_app()
    with app.app_context():
        approval = PendingApproval.query.filter_by(approval_id=approval_id).first()
        if not approval:
            click.echo(f"ERROR: Approval {approval_id} not found")
            return

        click.echo(f"\n=== {approval.title} ===")
        click.echo(f"Confidence: {float(approval.confidence):.2f}")
        click.echo(f"Files: {approval.blast_radius_files} | LOC: {approval.blast_radius_loc}")
        click.echo(f"\n{approval.diff}")

if __name__ == '__main__':
    cli()
