"use client";

import { useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { apiRequest, ApiClientError } from "@/lib/api/client";
import { useJobDetailObserver } from "@/features/jobs/hooks/useJobDetailObserver";

function formatEta(seconds?: number | null): string {
  if (typeof seconds !== "number" || Number.isNaN(seconds) || seconds < 0) {
    return "Calculating ETA...";
  }
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes}m ${remainder}s`;
}

export default function JobDetailPage() {
  const params = useParams<{ id?: string | string[] }>();
  const [retryError, setRetryError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const id = useMemo(() => {
    if (!params?.id) return null;
    return Array.isArray(params.id) ? params.id[0] : params.id;
  }, [params]);

  const observed = useJobDetailObserver(id);
  const job = observed.job;
  const percent = job?.percent_complete ?? 0;
  const isTerminal = job?.status === "completed" || job?.status === "failed" || job?.status === "failed_terminal" || job?.status === "cancelled";

  return (
    <div className="page-wrap">
      <div className="page-header">
        <h1 className="page-title">
          <span className="material-symbols-rounded" style={{ marginRight: 8 }}>work_history</span>
          Job {id ?? "unknown"}
        </h1>
        <p className="page-subtitle">SSE-first observation with polling fallback.</p>
      </div>

      <div className="page-body">
        {/* Transport indicator */}
        <div className="job-transport-bar">
          <span className="material-symbols-rounded" style={{ fontSize: 15 }}>
            {observed.mode === "sse" ? "wifi" : "sync"}
          </span>
          Transport: <strong>{observed.mode}</strong>
          {observed.degraded && (
            <span style={{ color: "var(--warning)", marginLeft: 8 }}>⚠ degraded</span>
          )}
        </div>

        {job ? (
          <div className="job-detail-card" data-testid="job-detail-progress">
            {/* Header row */}
            <div className="job-detail-header">
              <span style={{ fontSize: "0.9rem", color: "var(--muted)" }}>
                Step: <strong data-testid="job-current-step" style={{ color: "var(--text)" }}>{job.current_step_label ?? job.current_step ?? "Queued"}</strong>
              </span>
              <span
                className="job-status-badge"
                data-status={job.status}
              >
                {job.status}
              </span>
            </div>

            {/* Progress bar */}
            <div>
              <div className="progress-shell" aria-label="job-progress">
                <div
                  className="progress-bar"
                  data-testid="job-progress-bar"
                  style={{ width: `${Math.max(0, Math.min(100, percent))}%` }}
                />
              </div>
              <p className="muted" style={{ margin: "6px 0 0", fontSize: "0.78rem" }} data-testid="job-progress-percent">
                {percent.toFixed(1)}% complete
              </p>
            </div>

            {/* Stats grid */}
            <div className="job-detail-stats">
              <div className="job-stat-box">
                <span className="job-stat-label">ETA</span>
                <span className="job-stat-value" data-testid="job-eta">{formatEta(job.eta_seconds)}</span>
              </div>
              <div className="job-stat-box">
                <span className="job-stat-label">Processed</span>
                <span className="job-stat-value">{job.processed_items ?? 0} / {job.total_items ?? 0}</span>
              </div>
            </div>

            {/* Error message */}
            {job.error_message && (
              <p style={{ margin: 0, color: "var(--error)", fontSize: "0.825rem" }} data-testid="job-error-message">
                {job.error_message}
              </p>
            )}

            {/* Actions */}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {job.results_url && (
                <a
                  href={job.results_url}
                  className="btn-ghost"
                  style={{ fontSize: "0.8rem", padding: "7px 14px", textDecoration: "none" }}
                >
                  <span className="material-symbols-rounded" style={{ fontSize: 15, marginRight: 4 }}>download</span>
                  View results
                </a>
              )}
              {job.can_retry && isTerminal && id && (
                <button
                  className="btn-ghost"
                  type="button"
                  data-testid="job-retry-button"
                  disabled={retrying}
                  style={{ fontSize: "0.8rem" }}
                  onClick={() => {
                    setRetryError(null);
                    setRetrying(true);
                    void apiRequest<{ job_id: number }>(`/api/v1/jobs/${id}/retry`, { method: "POST" })
                      .then((result) => { window.location.assign(`/jobs/${result.job_id}`); })
                      .catch((reason: unknown) => {
                        if (reason instanceof ApiClientError) {
                          setRetryError(`${reason.normalized.detail} (HTTP ${reason.normalized.status})`);
                        } else if (reason instanceof Error) {
                          setRetryError(reason.message);
                        } else {
                          setRetryError("Retry request failed.");
                        }
                      })
                      .finally(() => setRetrying(false));
                  }}
                >
                  <span className="material-symbols-rounded" style={{ fontSize: 15, marginRight: 4 }}>replay</span>
                  {retrying ? "Retrying…" : "Retry job"}
                </button>
              )}
            </div>

            {retryError && (
              <p style={{ margin: 0, color: "var(--error)", fontSize: "0.8rem" }} data-testid="job-retry-error">
                {retryError}
              </p>
            )}
          </div>
        ) : (
          <div className="jobs-empty">
            <span className="material-symbols-rounded">hourglass_empty</span>
            <p>Waiting for job data…</p>
          </div>
        )}
      </div>
    </div>
  );
}
