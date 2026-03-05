"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { OperationalErrorCard } from "@/components/OperationalErrorCard";
import { apiRequest } from "@/lib/api/client";
import { stableDiagnosticId } from "@/lib/diagnostics";
import { useJobRehydrate } from "@/features/jobs/hooks/useJobRehydrate";
import { mapBackendStatusToLifecycle } from "@/features/jobs/observer/job-observer";

type JobsFilter = "all" | "running" | "failed" | "completed" | "cancelled";

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
  const [activeFilter, setActiveFilter] = useState<JobsFilter>("all");

  const sortedJobs = useMemo(() => [...jobs].sort((a, b) => b.id - a.id), [jobs]);

  const counts = useMemo(() => {
    const base = { running: 0, failed: 0, completed: 0, cancelled: 0 };
    for (const item of sortedJobs) {
      const badge = statusBadgeState(item.status);
      if (badge === "running") base.running += 1;
      if (badge === "failed") base.failed += 1;
      if (badge === "completed") base.completed += 1;
      if (badge === "cancelled") base.cancelled += 1;
    }
    return base;
  }, [sortedJobs]);

  const visibleJobs = useMemo(() => {
    if (activeFilter === "all") return sortedJobs;
    return sortedJobs.filter((item) => statusBadgeState(item.status) === activeFilter);
  }, [activeFilter, sortedJobs]);

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

  const combinedError = retryError || error;

  return (
    <div className="page-wrap" data-testid="jobs-workspace">
      <div className="page-header">
        <h1 className="page-title">
          <span className="material-symbols-rounded title-icon">work_history</span>
          Jobs
        </h1>
        <p className="page-subtitle">Track ingest and enrichment runs with retry controls.</p>
      </div>

      <div className="page-body">
        <section className="panel jobs-toolbar">
          <div>
            <strong className="forensic-card-title">Recent Jobs</strong>
            <p className="forensic-card-copy jobs-toolbar-copy">
              {isRehydrating ? "Refreshing from backend..." : `Loaded ${sortedJobs.length} jobs`}
            </p>
          </div>
          <button className="btn-ghost" type="button" onClick={() => void rehydrate()}>
            <span className="material-symbols-rounded icon-sm">refresh</span>
            Refresh
          </button>
        </section>

        <section className="panel jobs-filter-panel">
          <h2 className="forensic-card-title forensic-zero-top">Status Filters</h2>
          <div className="forensic-chip-row">
            <button className={`forensic-chip ${activeFilter === "all" ? "is-active" : ""}`} type="button" onClick={() => setActiveFilter("all")}>
              All ({sortedJobs.length})
            </button>
            <button className={`forensic-chip ${activeFilter === "running" ? "is-active" : ""}`} type="button" onClick={() => setActiveFilter("running")}>
              Running ({counts.running})
            </button>
            <button className={`forensic-chip ${activeFilter === "failed" ? "is-active" : ""}`} type="button" onClick={() => setActiveFilter("failed")}>
              Failed ({counts.failed})
            </button>
            <button className={`forensic-chip ${activeFilter === "completed" ? "is-active" : ""}`} type="button" onClick={() => setActiveFilter("completed")}>
              Completed ({counts.completed})
            </button>
            <button className={`forensic-chip ${activeFilter === "cancelled" ? "is-active" : ""}`} type="button" onClick={() => setActiveFilter("cancelled")}>
              Cancelled ({counts.cancelled})
            </button>
          </div>
        </section>

        {combinedError ? (
          <OperationalErrorCard
            title="Jobs request failed"
            detail={combinedError}
            diagnosticId={stableDiagnosticId(combinedError)}
            retryLabel="Retry jobs fetch"
            onRetry={() => { void rehydrate(); }}
          />
        ) : null}

        {visibleJobs.length === 0 ? (
          <section className="jobs-empty panel">
            <span className="material-symbols-rounded">inbox</span>
            <p>{sortedJobs.length === 0 ? "No jobs found yet." : "No jobs match this filter."}</p>
            <p className="muted">Create your first run from onboarding or chat bulk actions.</p>
            <Link className="btn-primary" href="/onboarding">Open onboarding</Link>
          </section>
        ) : (
          <div className="enrichment-review-layout">
            {visibleJobs.map((job) => {
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
                    <div className="jobs-card-head">
                      <strong className="forensic-card-title">
                        {job.job_name || `Job #${job.id}`}
                      </strong>
                      <span className="forensic-inline-note">ID: {job.id}</span>
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
                    <p className="auth-error jobs-card-error">{job.error_message}</p>
                  ) : null}

                  <div className="jobs-card-actions">
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
                        onClick={() => { void onRetry(job.id); }}
                        disabled={retryingJobId === job.id}
                      >
                        {retryingJobId === job.id ? "Retrying..." : "Retry job"}
                      </button>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
