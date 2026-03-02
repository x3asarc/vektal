'use client';

import { useState, useEffect } from 'react';
import './ApprovalQueue.css';

interface Approval {
  approval_id: string;
  title: string;
  confidence: number;
  blast_radius_files: number;
  blast_radius_loc: number;
  created_at: string;
  expires_at: string;
  type: string;
  status: string;
}

export function ApprovalQueue() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadApprovals();
  }, []);

  const loadApprovals = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/v1/approvals/');
      if (!res.ok) throw new Error('Failed to load approvals');
      const data = await res.json();
      setApprovals(data.approvals);
    } catch (err: any) {
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

      setApprovals(prev => prev.filter(a => a.approval_id !== approvalId));
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleReject = async (approvalId: string) => {
    const note = window.prompt('Rejection reason (optional):');
    if (note === null) return; // Cancelled

    try {
      const res = await fetch(`/api/v1/approvals/${approvalId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note })
      });
      if (!res.ok) throw new Error('Failed to reject');

      setApprovals(prev => prev.filter(a => a.approval_id !== approvalId));
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    }
  };

  if (loading) return <div className="loading">Loading approvals...</div>;
  if (error) return <div className="error-state">Error: {error}</div>;

  return (
    <div className="approval-queue-container">
      <header className="queue-header">
        <h2>Autonomous Approval Queue</h2>
        <button className="btn-refresh" onClick={loadApprovals}>Refresh</button>
      </header>

      {approvals.length === 0 ? (
        <div className="empty-state">
          <p>No pending approvals. The system is operating autonomously or no fixes are currently queued.</p>
        </div>
      ) : (
        <div className="approval-list">
          {approvals.map(approval => (
            <div key={approval.approval_id} className="approval-card">
              <div className="card-top">
                <div className="title-group">
                  <h3>{approval.title}</h3>
                  <span className={`type-badge type-${approval.type.toLowerCase()}`}>{approval.type}</span>
                </div>
                <div className="confidence-meter">
                  <div className="meter-label">Confidence</div>
                  <div className="meter-bar">
                    <div 
                      className="meter-fill" 
                      style={{ width: `${approval.confidence * 100}%`, backgroundColor: approval.confidence > 0.8 ? '#4caf50' : '#ffa000' }}
                    ></div>
                  </div>
                  <div className="meter-value">{(approval.confidence * 100).toFixed(0)}%</div>
                </div>
              </div>

              <div className="card-meta">
                <span className="meta-item">Files: <strong>{approval.blast_radius_files}</strong></span>
                <span className="meta-item">LOC: <strong>{approval.blast_radius_loc}</strong></span>
                <span className="meta-item">Queued: <strong>{new Date(approval.created_at).toLocaleString()}</strong></span>
              </div>

              <div className="card-actions">
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
                <button className="btn-details" onClick={() => window.location.href = `/approvals/${approval.approval_id}`}>
                  View Details
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
