'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { OperationalErrorCard } from "@/components/OperationalErrorCard";
import { stableDiagnosticId } from "@/lib/diagnostics";

interface Approval {
  approval_id: string;
  title: string;
  confidence: number;
  blast_radius_files: number;
  blast_radius_loc?: number;
  created_at: string;
  expires_at: string | null;
  type: string;
  status: string;
  priority?: "low" | "normal" | "high" | "critical";
}

type ApprovalListResponse = {
  approvals: Approval[];
};

type QueueMode = "standard" | "polling";

function parseError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Unexpected approval queue error.";
}

function relativeAge(createdAt: string): string {
  const diffMs = Date.now() - new Date(createdAt).getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  if (diffMinutes < 1) return "just now";
  if (diffMinutes < 60) return `${diffMinutes}m`;
  const hours = Math.floor(diffMinutes / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

function riskLabel(approval: Approval): "high" | "medium" | "low" {
  if (approval.priority === "critical" || approval.confidence < 0.7) return "high";
  if (approval.priority === "high" || approval.confidence < 0.82) return "medium";
  return "low";
}

export function ApprovalQueue() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<QueueMode>("standard");
  const [pendingAction, setPendingAction] = useState<string | null>(null);

  const loadApprovals = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/v1/approvals/');
      if (!res.ok) throw new Error('Failed to load approvals');
      const data: ApprovalListResponse = await res.json() as ApprovalListResponse;
      setApprovals(data.approvals);
      setError(null);
    } catch (err: unknown) {
      setError(parseError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadApprovals();
  }, [loadApprovals]);

  useEffect(() => {
    if (mode !== "polling") return;
    const interval = window.setInterval(() => {
      void loadApprovals();
    }, 15_000);
    return () => window.clearInterval(interval);
  }, [mode, loadApprovals]);

  const sortedApprovals = useMemo(
    () => [...approvals].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [approvals],
  );

  const handleApprove = async (approvalId: string) => {
    try {
      setPendingAction(approvalId);
      const res = await fetch(`/api/v1/approvals/${approvalId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) throw new Error('Failed to approve');
      setApprovals((prev) => prev.filter((a) => a.approval_id !== approvalId));
      setError(null);
    } catch (err: unknown) {
      setError(parseError(err));
    } finally {
      setPendingAction(null);
    }
  };

  const handleReject = async (approvalId: string) => {
    const note = window.prompt('Rejection reason (optional):');
    if (note === null) return;

    try {
      setPendingAction(approvalId);
      const res = await fetch(`/api/v1/approvals/${approvalId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note }),
      });
      if (!res.ok) throw new Error('Failed to reject');
      setApprovals((prev) => prev.filter((a) => a.approval_id !== approvalId));
      setError(null);
    } catch (err: unknown) {
      setError(parseError(err));
    } finally {
      setPendingAction(null);
    }
  };

  return (
    <div className="approval-queue-container">
      <header className="queue-header">
        <h2>Pending Approvals</h2>
        <div className="forensic-actions">
          <button className="btn-ghost" type="button" onClick={() => { void loadApprovals(); }}>
            Refresh
          </button>
          <button
            className="btn-ghost"
            type="button"
            onClick={() => setMode((prev) => (prev === "standard" ? "polling" : "standard"))}
          >
            {mode === "polling" ? "Switch to standard" : "Switch to polling"}
          </button>
        </div>
      </header>

      {loading ? (
        <div className="loading">Loading approvals...</div>
      ) : null}

      {error ? (
        <OperationalErrorCard
          title="Failed to load approvals"
          detail={error}
          diagnosticId={stableDiagnosticId(error)}
          retryLabel="Retry load"
          onRetry={() => { void loadApprovals(); }}
          secondaryLabel={mode === "polling" ? "Use standard mode" : "Use polling mode"}
          onSecondaryAction={() => setMode((prev) => (prev === "standard" ? "polling" : "standard"))}
        />
      ) : null}

      {!loading && !error && sortedApprovals.length === 0 ? (
        <div className="empty-state">
          <p>No pending approvals. The system is operating autonomously or no fixes are currently queued.</p>
        </div>
      ) : null}

      {!loading && !error && sortedApprovals.length > 0 ? (
        <div className="forensic-table-wrap">
          <table className="forensic-table approval-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Risk</th>
                <th>Source</th>
                <th>Age</th>
                <th>Files</th>
                <th>LOC</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedApprovals.map((approval) => (
                <tr key={approval.approval_id}>
                  <td>
                    <strong>{approval.title}</strong>
                  </td>
                  <td>
                    <span className="forensic-state-tag" data-state={riskLabel(approval) === "high" ? "warning" : "ok"}>
                      {riskLabel(approval)}
                    </span>
                  </td>
                  <td>{approval.type}</td>
                  <td>{relativeAge(approval.created_at)}</td>
                  <td>{approval.blast_radius_files}</td>
                  <td>{approval.blast_radius_loc ?? "n/a"}</td>
                  <td>
                    <div className="forensic-actions">
                      <button
                        className="btn-primary"
                        type="button"
                        onClick={() => { void handleApprove(approval.approval_id); }}
                        disabled={pendingAction === approval.approval_id}
                      >
                        Approve
                      </button>
                      <button
                        className="btn-ghost"
                        type="button"
                        onClick={() => { void handleReject(approval.approval_id); }}
                        disabled={pendingAction === approval.approval_id}
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
