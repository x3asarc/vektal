"use client";

import { useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { OperationalErrorCard } from "@/components/OperationalErrorCard";
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
          <span className="material-symbols-rounded title-icon">work_history</span>
          Job {id ?? "unknown"}
        </h1>
        <p className="page-subtitle">SSE-first observation with polling fallback.</p>
      </div>

      <div className="page-body">
        <div className="job-transport-bar">
          <span className="material-symbols-rounded icon-sm">
            {observed.mode === "sse" ? "wifi" : "sync"}
          </span>
          Transport: <strong>{observed.mode}</strong>
          {observed.degraded ? (
            <span className="job-transport-warning">degraded</span>
          ) : null}
        </div>

        <div className="forensic-actions">
          <button className="btn-ghost" type="button" onClick={() => { void observed.pollNow(); }}>
            Poll now
          </button>
          <button className="btn-ghost" type="button" onClick={observed.reconnect}>
            Reconnect stream
          </button>
        </div>

        {observed.error ? (
          <OperationalErrorCard
            title="Job transport degraded"
            detail={observed.error}
            retryLabel="Retry poll"
            onRetry={() => { void observed.pollNow(); }}
            secondaryLabel="Reconnect stream"
            onSecondaryAction={observed.reconnect}
          />
        ) : null}

        {job ? (
          <div className="job-detail-card" data-testid="job-detail-progress">
            <div className="job-detail-header">
              <span className="job-step-line">
                Step: <strong data-testid="job-current-step">{job.current_step_label ?? job.current_step ?? "Queued"}</strong>
              </span>
              <span
                className="job-status-badge"
                data-status={job.status}
              >
                {job.status}
              </span>
            </div>

            <div>
              <div className="progress-shell" aria-label="job-progress">
                <div
                  className="progress-bar"
                  data-testid="job-progress-bar"
                  style={{ width: `${Math.max(0, Math.min(100, percent))}%` }}
                />
              </div>
              <p className="muted job-progress-copy" data-testid="job-progress-percent">
                {percent.toFixed(1)}% complete
              </p>
            </div>

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

            {job.error_message ? (
              <p className="job-error" data-testid="job-error-message">
                {job.error_message}
              </p>
            ) : null}

            <div className="job-detail-actions">
              {job.results_url ? (
                <a
                  href={job.results_url}
                  className="btn-ghost job-link-btn"
                >
                  <span className="material-symbols-rounded icon-sm">download</span>
                  View results
                </a>
              ) : null}
              {job.can_retry && isTerminal && id ? (
                <button
                  className="btn-ghost btn-compact"
                  type="button"
                  data-testid="job-retry-button"
                  disabled={retrying}
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
                  <span className="material-symbols-rounded icon-sm">replay</span>
                  {retrying ? "Retrying..." : "Retry job"}
                </button>
              ) : null}
            </div>

            {retryError ? (
              <p className="job-error" data-testid="job-retry-error">
                {retryError}
              </p>
            ) : null}
          </div>
        ) : (
          <div className="jobs-empty">
            <span className="material-symbols-rounded">hourglass_empty</span>
            <p>Waiting for job data...</p>
          </div>
        )}

        <section className="panel">
          <h2 className="forensic-card-title forensic-zero-top">Event Timeline</h2>
          {observed.events.length === 0 ? (
            <p className="forensic-card-copy">No transport events yet.</p>
          ) : (
            <ul className="job-event-list">
              {observed.events.map((event) => (
                <li key={event.id}>
                  <span className="forensic-inline-note">{new Date(event.at).toLocaleTimeString()} / {event.kind}</span>
                  <span>{event.message}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
