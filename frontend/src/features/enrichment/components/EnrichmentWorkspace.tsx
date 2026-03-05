"use client";

import { useEffect, useMemo, useState } from "react";
import {
  EnrichmentLifecycleResponse,
  applyEnrichmentRun,
  approveEnrichmentRun,
  fetchEnrichmentReview,
  startEnrichmentRun,
} from "@/features/enrichment/api/enrichment-api";
import { EnrichmentConflictPanel } from "@/features/enrichment/components/EnrichmentConflictPanel";
import { EnrichmentReviewTable } from "@/features/enrichment/components/EnrichmentReviewTable";
import { EnrichmentRunConfigurator } from "@/features/enrichment/components/EnrichmentRunConfigurator";

type RecentRun = {
  runId: number;
  status: string;
  runProfile: string;
  targetLanguage: string;
  allowed: number;
  blocked: number;
  createdAt: string;
};

const RECENT_RUNS_KEY = "enrichment.recentRuns.v1";

export function EnrichmentWorkspace() {
  const [run, setRun] = useState<EnrichmentLifecycleResponse | null>(null);
  const [recentRuns, setRecentRuns] = useState<RecentRun[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applyResult, setApplyResult] = useState<{ job_id: number; queue: string } | null>(null);

  const rows = useMemo(() => {
    if (!run) return [];
    return [...run.write_plan.allowed, ...run.write_plan.blocked];
  }, [run]);

  const preflightSummary = useMemo(() => {
    if (!run) return null;
    const requiresAction = run.write_plan.allowed.filter((item) => item.requires_user_action).length;
    return {
      total: run.write_plan.counts.total,
      allowed: run.write_plan.counts.allowed,
      blocked: run.write_plan.counts.blocked,
      selected: selectedIds.size,
      requiresAction,
      stale: run.is_stale,
    };
  }, [run, selectedIds.size]);

  function recordRunHistory(source: EnrichmentLifecycleResponse) {
    const snapshot: RecentRun = {
      runId: source.run_id,
      status: source.status,
      runProfile: source.run_profile,
      targetLanguage: source.target_language,
      allowed: source.write_plan.counts.allowed,
      blocked: source.write_plan.counts.blocked,
      createdAt: new Date().toISOString(),
    };
    setRecentRuns((previous) => {
      const next = [snapshot, ...previous.filter((item) => item.runId !== snapshot.runId)].slice(0, 8);
      try {
        window.localStorage.setItem(RECENT_RUNS_KEY, JSON.stringify(next));
      } catch {
        // Ignore storage failures.
      }
      return next;
    });
  }

  async function handleStart(payload: Parameters<typeof startEnrichmentRun>[0]) {
    setIsBusy(true);
    setError(null);
    setApplyResult(null);
    try {
      const response = await startEnrichmentRun(payload);
      setRun(response);
      recordRunHistory(response);
      const autoSelect = new Set<number>();
      for (const row of response.write_plan.allowed) {
        if (!row.is_blocked && typeof row.item_id === "number") {
          autoSelect.add(row.item_id);
        }
      }
      setSelectedIds(autoSelect);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start enrichment run.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRefresh() {
    if (!run) return;
    setIsBusy(true);
    setError(null);
    try {
      const response = await fetchEnrichmentReview(run.run_id);
      setRun(response);
      recordRunHistory(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh run.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleApprove() {
    if (!run) return;
    setIsBusy(true);
    setError(null);
    try {
      const response = await approveEnrichmentRun(run.run_id, {
        approve_all: selectedIds.size === 0,
        approved_item_ids: Array.from(selectedIds),
        rejected_item_ids: [],
        reviewer_note: "Approved from workspace",
      });
      setRun(response);
      recordRunHistory(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval failed.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleApply() {
    if (!run) return;
    setIsBusy(true);
    setError(null);
    try {
      const response = await applyEnrichmentRun(run.run_id, {
        apply_mode: "immediate",
        confirm_apply: true,
      });
      setApplyResult({ job_id: response.job_id, queue: response.queue });
      const refreshed = await fetchEnrichmentReview(run.run_id);
      setRun(refreshed);
      recordRunHistory(refreshed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Apply failed.");
    } finally {
      setIsBusy(false);
    }
  }

  function toggleSelected(itemId: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(itemId)) {
        next.delete(itemId);
      } else {
        next.add(itemId);
      }
      return next;
    });
  }

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(RECENT_RUNS_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as RecentRun[];
      if (Array.isArray(parsed) && recentRuns.length === 0) {
        setRecentRuns(parsed.slice(0, 8));
      }
    } catch {
      // Ignore history loading failures.
    }
  }, [recentRuns.length]);

  return (
    <div className="page-wrap" data-testid="enrichment-workspace">
      {/* Page header */}
      <div className="page-header">
        <h1 className="page-title">
          <span className="material-symbols-rounded title-icon">inventory_2</span>
          Product Enrichment
        </h1>
        <p className="page-subtitle">Governed enrichment with dry-run TTL, policy lineage, and queue-backed apply.</p>
      </div>

      {/* Scrollable body */}
      <div className="page-body">
        {error ? <p className="enrichment-error">{error}</p> : null}

        <EnrichmentRunConfigurator onStart={handleStart} isSubmitting={isBusy} />

        {preflightSummary ? (
          <section className="panel">
            <h2 className="forensic-card-title forensic-zero-top">Preflight Summary</h2>
            <div className="forensic-chip-row">
              <span className="forensic-chip">Total: {preflightSummary.total}</span>
              <span className="forensic-chip">Allowed: {preflightSummary.allowed}</span>
              <span className="forensic-chip">Blocked: {preflightSummary.blocked}</span>
              <span className="forensic-chip">Requires action: {preflightSummary.requiresAction}</span>
              <span className="forensic-chip">Selected to approve: {preflightSummary.selected}</span>
              <span className={`forensic-chip ${preflightSummary.stale ? "is-warning" : ""}`}>
                TTL: {preflightSummary.stale ? "stale" : "fresh"}
              </span>
            </div>
          </section>
        ) : null}

        {run ? (
          <div className="enrichment-run-summary" data-testid="enrichment-run-summary">
            <h2 className="forensic-card-title">Run Summary</h2>
            <div className="enrichment-run-meta forensic-chip-row">
              <span className="enrichment-badge">Run <strong>#{run.run_id}</strong></span>
              <span className="enrichment-badge">Profile: <strong>{run.run_profile}</strong></span>
              <span className="enrichment-badge">Lang: <strong>{run.target_language}</strong></span>
              <span className="enrichment-badge">Status: <strong>{run.status}</strong></span>
              <span className="enrichment-badge">Oracle: <strong>{run.oracle_decision}</strong></span>
              {run.is_stale && <span className="enrichment-badge enrichment-stale-badge">TTL stale</span>}
            </div>
            <div className="enrichment-run-meta forensic-chip-row enrichment-meta-row">
              <span className="enrichment-badge">Allowed: <strong>{run.write_plan.counts.allowed}</strong></span>
              <span className="enrichment-badge">Blocked: <strong>{run.write_plan.counts.blocked}</strong></span>
              <span className="enrichment-badge">Approved: <strong>{run.write_plan.counts.approved ?? 0}</strong></span>
              <span className="enrichment-badge">Total: <strong>{run.write_plan.counts.total}</strong></span>
            </div>
            <div className="forensic-actions">
              <button className="btn-ghost btn-compact" type="button" onClick={() => { void handleRefresh(); }} disabled={isBusy}>
                <span className="material-symbols-rounded icon-sm">refresh</span>
                Refresh
              </button>
              <button className="btn-ghost btn-compact" type="button" onClick={() => { void handleApprove(); }} disabled={isBusy || run.is_stale}>
                <span className="material-symbols-rounded icon-sm">check_circle</span>
                Approve selection
              </button>
              <button className="btn-primary btn-compact" type="button" onClick={() => { void handleApply(); }} disabled={isBusy || run.is_stale}>
                <span className="material-symbols-rounded icon-sm">send</span>
                Apply approved
              </button>
            </div>
          </div>
        ) : null}

        {recentRuns.length > 0 ? (
          <section className="panel">
            <h2 className="forensic-card-title forensic-zero-top">Recent Enrichment Runs</h2>
            <div className="forensic-table-wrap">
              <table className="forensic-table">
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Status</th>
                    <th>Profile</th>
                    <th>Language</th>
                    <th>Allowed</th>
                    <th>Blocked</th>
                  </tr>
                </thead>
                <tbody>
                  {recentRuns.map((item) => (
                    <tr key={item.runId}>
                      <td>#{item.runId}</td>
                      <td>{item.status}</td>
                      <td>{item.runProfile}</td>
                      <td>{item.targetLanguage}</td>
                      <td>{item.allowed}</td>
                      <td>{item.blocked}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}

        {applyResult ? (
          <div className="panel enrichment-apply-result" data-testid="enrichment-apply-result">
            <span className="material-symbols-rounded enrichment-success-icon">check_circle</span>
            <p className="muted forensic-zero">
              Job <strong className="enrichment-result-strong">#{applyResult.job_id}</strong> queued on <strong className="enrichment-result-strong">{applyResult.queue}</strong>.
            </p>
          </div>
        ) : null}

        {run ? (
          <>
            <EnrichmentReviewTable rows={rows} selectedIds={selectedIds} onToggle={toggleSelected} />
            <EnrichmentConflictPanel
              blockedRows={run.write_plan.blocked}
              protectedColumns={run.protected_columns}
            />
          </>
        ) : null}
      </div>
    </div>
  );
}
