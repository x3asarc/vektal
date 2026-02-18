"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { apiRequest } from "@/lib/api/client";
import { useJobRehydrate } from "@/features/jobs/hooks/useJobRehydrate";
import { mapBackendStatusToLifecycle } from "@/features/jobs/observer/job-observer";

function statusBadgeState(status: string): string {
  const lifecycle = mapBackendStatusToLifecycle(status);
  if (lifecycle === "success") return "completed";
  if (lifecycle === "cancelled") return "cancelled";
  if (lifecycle === "error") return "failed";
  return "running";
}

export function JobsWorkspace() {
  const { jobs, error, isRehydrating, rehydrate } = useJobRehydrate();
  const [retryingJobId, setRetryingJobId] = useState<number | null>(null);
  const [retryError, setRetryError] = useState<string | null>(null);

  const sortedJobs = useMemo(() => [...jobs].sort((a, b) => b.id - a.id), [jobs]);

  async function onRetry(jobId: number) {
    setRetryError(null);
    setRetryingJobId(jobId);
    try {
      const result = await apiRequest<{ job_id: number }>(`/api/v1/jobs/${jobId}/retry`, {
        method: "POST",
      });
      window.location.assign(`/jobs/${result.job_id}`);
    } catch (err) {
      setRetryError(err instanceof Error ? err.message : "Retry failed.");
    } finally {
      setRetryingJobId(null);
    }
  }

  return (
    <div className="page-wrap" data-testid="jobs-workspace">
      <div className="page-header">
        <h1 className="page-title">
          <span className="material-symbols-rounded" style={{ marginRight: 8 }}>work_history</span>
          Jobs
        </h1>
        <p className="page-subtitle">Track ingest and enrichment runs with retry controls.</p>
      </div>

      <div className="page-body">
        <section className="panel" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <div>
            <strong style={{ fontSize: "0.9rem" }}>Recent Jobs</strong>
            <p className="muted" style={{ margin: "4px 0 0", fontSize: "0.78rem" }}>
              {isRehydrating ? "Refreshing from backend..." : `Loaded ${sortedJobs.length} jobs`}
            </p>
          </div>
          <button className="btn-ghost" type="button" onClick={() => void rehydrate()}>
            <span className="material-symbols-rounded" style={{ fontSize: 15, marginRight: 4 }}>refresh</span>
            Refresh
          </button>
        </section>

        {error ? <p className="auth-error">Jobs error: {error}</p> : null}
        {retryError ? <p className="auth-error">Retry error: {retryError}</p> : null}

        {sortedJobs.length === 0 ? (
          <section className="jobs-empty panel">
            <span className="material-symbols-rounded">inbox</span>
            <p>No jobs found yet.</p>
            <p className="muted">Create your first run from onboarding or chat bulk actions.</p>
            <Link className="btn-primary" href="/onboarding">Open onboarding</Link>
          </section>
        ) : (
          sortedJobs.map((job) => {
            const badgeState = statusBadgeState(job.status);
            const total = Math.max(job.total_items ?? 0, 0);
            const processed = Math.max(job.processed_items ?? 0, 0);
            const successful = Math.max(job.successful_items ?? 0, 0);
            const failed = Math.max(job.failed_items ?? 0, 0);
            const percent =
              typeof job.percent_complete === "number"
                ? Math.min(100, Math.max(0, Math.round(job.percent_complete)))
                : total > 0
                  ? Math.round((processed / total) * 100)
                  : 0;

            return (
              <article className="job-detail-card" key={job.id}>
                <div className="job-detail-header">
                  <div style={{ display: "grid", gap: 4 }}>
                    <strong style={{ fontSize: "0.95rem", color: "var(--text)" }}>
                      {job.job_name || `Job #${job.id}`}
                    </strong>
                    <span className="muted" style={{ fontSize: "0.75rem" }}>ID: {job.id}</span>
                  </div>
                  <span className="job-status-badge" data-status={badgeState}>
                    {job.status}
                  </span>
                </div>

                <div className="job-detail-stats">
                  <div className="job-stat-box">
                    <span className="job-stat-label">Processed</span>
                    <span className="job-stat-value">{processed}/{total}</span>
                  </div>
                  <div className="job-stat-box">
                    <span className="job-stat-label">Successful</span>
                    <span className="job-stat-value">{successful}</span>
                  </div>
                  <div className="job-stat-box">
                    <span className="job-stat-label">Failed</span>
                    <span className="job-stat-value">{failed}</span>
                  </div>
                  <div className="job-stat-box">
                    <span className="job-stat-label">Progress</span>
                    <span className="job-stat-value">{percent}%</span>
                  </div>
                </div>

                {job.error_message ? (
                  <p className="auth-error" style={{ margin: 0 }}>{job.error_message}</p>
                ) : null}

                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <Link className="btn-ghost" href={`/jobs/${job.id}`}>
                    View details
                  </Link>
                  {job.results_url ? (
                    <Link className="btn-ghost" href={job.results_url}>
                      View results
                    </Link>
                  ) : null}
                  {job.can_retry ? (
                    <button
                      className="btn-primary"
                      type="button"
                      onClick={() => void onRetry(job.id)}
                      disabled={retryingJobId === job.id}
                    >
                      {retryingJobId === job.id ? "Retrying..." : "Retry job"}
                    </button>
                  ) : null}
                </div>
              </article>
            );
          })
        )}
      </div>
    </div>
  );
}

