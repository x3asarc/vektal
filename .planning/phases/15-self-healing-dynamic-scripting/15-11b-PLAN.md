---
phase: 15-self-healing-dynamic-scripting
plan: 11b
type: execute
wave: 5
depends_on: ["15-11a"]
files_modified:
  - src/cli/approvals.py
  - frontend/src/features/approvals/components/ApprovalQueue.tsx
  - frontend/src/features/approvals/pages/ApprovalsPage.tsx
autonomous: false  # Contains checkpoint task

must_haves:
  truths:
    - "Approvals visible in both CLI and web UI"
    - "Users can approve or reject from CLI with simple commands"
    - "Web UI displays approval queue with real-time updates"
  artifacts:
    - path: "src/cli/approvals.py"
      provides: "CLI for approval management"
      exports: []
    - path: "frontend/src/features/approvals/components/ApprovalQueue.tsx"
      provides: "Web UI for approval queue"
      exports: ["ApprovalQueue"]
  key_links:
    - from: "src/cli/approvals.py"
      to: "src/models/pending_approvals.py"
      via: "Direct database queries"
      pattern: "PendingApproval\\.query"
    - from: "frontend/src/features/approvals/components/ApprovalQueue.tsx"
      to: "src/api/v1/approvals.py"
      via: "fetch('/api/v1/approvals')"
      pattern: "fetch.*api/v1/approvals"
---

<objective>
Implement CLI and web UI for approval queue management.

Purpose: Enable human approval workflow from both command line and browser
Output: Working CLI commands and React components for approval management
</objective>

<execution_context>
@C:/Users/Hp/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Hp/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/15-self-healing-dynamic-scripting/15-ARCHITECTURE-LOCKED.md (Section 6: Approval Queue System Design)
@.planning/phases/15-self-healing-dynamic-scripting/15-11a-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Create CLI for approval management</name>
  <files>src/cli/approvals.py</files>
  <action>
CLI from 15-ARCHITECTURE-LOCKED.md Section 6.C:

```python
#!/usr/bin/env python
import click
from datetime import datetime
from src.models.pending_approvals import PendingApproval, ApprovalStatus

@click.group()
def cli():
    """Approval queue management."""
    pass

@cli.command()
def list():
    """List pending approvals."""
    approvals = PendingApproval.query.filter_by(status=ApprovalStatus.PENDING).all()

    click.echo(f"PENDING APPROVALS ({len(approvals)})")
    for i, a in enumerate(approvals, 1):
        age = (datetime.now() - a.created_at).total_seconds() / 3600
        click.echo(f"\n[{i}] {a.title} (confidence: {a.confidence:.2f})")
        click.echo(f"    Files: {a.blast_radius_files} | LOC: {a.blast_radius_loc} | Age: {age:.1f}h")
        click.echo(f"    ID: {a.approval_id}")
        click.echo(f"    → python src/cli/approvals.py approve {a.approval_id}")

@cli.command()
@click.argument('approval_id')
@click.option('--note', default=None)
def approve(approval_id, note):
    """Approve pending approval."""
    approval = PendingApproval.query.filter_by(approval_id=approval_id).first()
    if not approval:
        click.echo(f"ERROR: Approval {approval_id} not found")
        return

    approval.approve(user_id=1, note=note)  # CLI user ID = 1
    click.echo(f"✓ Approved: {approval.title}")

@cli.command()
@click.argument('approval_id')
@click.option('--note', default=None)
def reject(approval_id, note):
    """Reject pending approval."""
    approval = PendingApproval.query.filter_by(approval_id=approval_id).first()
    if not approval:
        click.echo(f"ERROR: Approval {approval_id} not found")
        return

    approval.reject(user_id=1, note=note)
    click.echo(f"✓ Rejected: {approval.title}")

@cli.command()
@click.argument('approval_id')
def diff(approval_id):
    """View approval diff."""
    approval = PendingApproval.query.filter_by(approval_id=approval_id).first()
    if not approval:
        click.echo(f"ERROR: Approval {approval_id} not found")
        return

    click.echo(f"\n=== {approval.title} ===")
    click.echo(f"Confidence: {approval.confidence:.2f}")
    click.echo(f"Files: {approval.blast_radius_files} | LOC: {approval.blast_radius_loc}")
    click.echo(f"\n{approval.diff}")

if __name__ == '__main__':
    cli()
```
  </action>
  <verify>
```bash
python src/cli/approvals.py list
```
  </verify>
  <done>CLI enables approval management from command line</done>
</task>

<task type="auto">
  <name>Create web UI for approval queue</name>
  <files>frontend/src/features/approvals/components/ApprovalQueue.tsx</files>
  <action>
React component for approval queue with API integration:

```tsx
import { useState, useEffect } from 'react';

interface Approval {
  approval_id: string;
  title: string;
  confidence: number;
  blast_radius_files: number;
  blast_radius_loc: number;
  created_at: string;
  expires_at: string;
  type: string;
}

export function ApprovalQueue() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Wire to REST API from 15-11a Task 2
  useEffect(() => {
    loadApprovals();
  }, []);

  const loadApprovals = async () => {
    try {
      const res = await fetch('/api/v1/approvals');
      if (!res.ok) throw new Error('Failed to load approvals');
      const data = await res.json();
      setApprovals(data.approvals);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (approvalId: string) => {
    try {
      const res = await fetch(`/api/v1/approvals/${approvalId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!res.ok) throw new Error('Failed to approve');

      setApprovals(approvals.filter(a => a.approval_id !== approvalId));
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleReject = async (approvalId: string) => {
    const note = prompt('Rejection reason (optional):');
    try {
      const res = await fetch(`/api/v1/approvals/${approvalId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note })
      });
      if (!res.ok) throw new Error('Failed to reject');

      setApprovals(approvals.filter(a => a.approval_id !== approvalId));
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  if (loading) return <div>Loading approvals...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="approval-queue">
      <h2>Pending Approvals ({approvals.length})</h2>

      {approvals.length === 0 && (
        <p className="empty-state">No pending approvals</p>
      )}

      {approvals.map(approval => (
        <div key={approval.approval_id} className="approval-card">
          <div className="approval-header">
            <h3>{approval.title}</h3>
            <span className="approval-type">{approval.type}</span>
          </div>

          <div className="approval-metrics">
            <span>Confidence: {(approval.confidence * 100).toFixed(0)}%</span>
            <span>Files: {approval.blast_radius_files}</span>
            <span>LOC: {approval.blast_radius_loc}</span>
          </div>

          <div className="approval-actions">
            <button
              className="btn-approve"
              onClick={() => handleApprove(approval.approval_id)}
            >
              Approve
            </button>
            <button
              className="btn-reject"
              onClick={() => handleReject(approval.approval_id)}
            >
              Reject
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
```
  </action>
  <verify>
```bash
npm --prefix frontend run test -- ApprovalQueue
```
  </verify>
  <done>Web UI displays approval queue with approve/reject actions</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Human verification checkpoint: Validate approval queue UI accessibility</name>
  <action>
Present approval queue interfaces for human review:

1. CLI implementation complete:
   - list, approve, reject, diff commands
   - Direct database queries to pending_approvals
   - User-friendly output with age, confidence, blast radius

2. Web UI implementation complete:
   - ApprovalQueue component with real-time updates
   - Approve/reject actions with REST API integration
   - Metrics display (confidence, files, LOC)
   - Empty state handling

3. Both interfaces connected to same approval backend (15-11a API)
  </action>
  <verify>
Confirm the following:

1. Create test approval:
   ```bash
   python -c "
   from src.models.pending_approvals import PendingApproval
   PendingApproval.create_approval(
       type='code_change',
       title='Test approval',
       description='Test',
       diff='...',
       confidence=0.85
   )
   "
   ```

2. List via CLI:
   ```bash
   python src/cli/approvals.py list
   ```

3. View in web UI:
   - Navigate to `/approvals` in browser
   - Verify approval appears in queue
   - Check metrics display (confidence, files, LOC)

4. Approve via CLI:
   ```bash
   python src/cli/approvals.py approve <approval_id>
   ```

5. Verify removed from queue in both CLI and UI

Expected: Approval visible in both interfaces, approve/reject works from both, no UI/UX issues
  </verify>
  <done>Human confirms approval queue works correctly in both CLI and web UI with no usability issues</done>
  <files>
    - src/cli/approvals.py
    - frontend/src/features/approvals/components/ApprovalQueue.tsx
    - scripts/checkpoints/log_approval.py
  </files>
</task>

</tasks>

<verification>
- CLI list, approve, reject, diff commands work
- Web UI fetches approvals from REST API (15-11a)
- Approve/reject actions update database and refresh UI
- Both interfaces access same approval queue
</verification>

<success_criteria>
1. CLI supports list, approve, reject, diff commands
2. Web UI displays approval queue with real-time updates
3. Both CLI and UI use same backend (15-11a API)
4. Approve/reject actions remove from pending queue
5. Error handling for network failures and not found cases
6. UI includes empty state when no approvals pending
</success_criteria>

<output>
After completion, create `.planning/phases/15-self-healing-dynamic-scripting/15-11b-SUMMARY.md`
</output>
