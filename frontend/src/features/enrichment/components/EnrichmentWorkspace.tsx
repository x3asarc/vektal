"use client";

import { useMemo, useState } from "react";
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

export function EnrichmentWorkspace() {
  const [run, setRun] = useState<EnrichmentLifecycleResponse | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applyResult, setApplyResult] = useState<{ job_id: number; queue: string } | null>(null);

  const rows = useMemo(() => {
    if (!run) return [];
    return [...run.write_plan.allowed, ...run.write_plan.blocked];
  }, [run]);

  async function handleStart(payload: Parameters<typeof startEnrichmentRun>[0]) {
    setIsBusy(true);
    setError(null);
    setApplyResult(null);
    try {
      const response = await startEnrichmentRun(payload);
      setRun(response);
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

  return (
    <div className="page-wrap" data-testid="enrichment-workspace">
      {/* Page header */}
      <div className="page-header">
        <h1 className="page-title">
          <span className="material-symbols-rounded" style={{ marginRight: 8 }}>inventory_2</span>
          Product Enrichment
        </h1>
        <p className="page-subtitle">Governed enrichment with dry-run TTL, policy lineage, and queue-backed apply.</p>
      </div>

      {/* Scrollable body */}
      <div className="page-body">
        {error ? <p style={{ color: "var(--error)", margin: 0 }}>{error}</p> : null}

        <EnrichmentRunConfigurator onStart={handleStart} isSubmitting={isBusy} />

        {run ? (
          <div className="enrichment-run-summary" data-testid="enrichment-run-summary">
            <h2>Run Summary</h2>
            <div className="enrichment-run-meta">
              <span className="enrichment-badge">Run <strong>#{run.run_id}</strong></span>
              <span className="enrichment-badge">Profile: <strong>{run.run_profile}</strong></span>
              <span className="enrichment-badge">Lang: <strong>{run.target_language}</strong></span>
              <span className="enrichment-badge">Status: <strong>{run.status}</strong></span>
              <span className="enrichment-badge">Oracle: <strong>{run.oracle_decision}</strong></span>
              {run.is_stale && <span className="enrichment-badge" style={{ color: "var(--warning)", borderColor: "rgba(251,191,36,0.3)" }}>TTL stale</span>}
            </div>
            <div className="enrichment-run-meta" style={{ gap: 6 }}>
              <span className="enrichment-badge">Allowed: <strong>{run.write_plan.counts.allowed}</strong></span>
              <span className="enrichment-badge">Blocked: <strong>{run.write_plan.counts.blocked}</strong></span>
              <span className="enrichment-badge">Approved: <strong>{run.write_plan.counts.approved ?? 0}</strong></span>
              <span className="enrichment-badge">Total: <strong>{run.write_plan.counts.total}</strong></span>
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button className="btn-ghost" type="button" onClick={() => { void handleRefresh(); }} disabled={isBusy} style={{ fontSize: "0.8rem" }}>
                <span className="material-symbols-rounded" style={{ fontSize: 15, marginRight: 4 }}>refresh</span>
                Refresh
              </button>
              <button className="btn-ghost" type="button" onClick={() => { void handleApprove(); }} disabled={isBusy || run.is_stale} style={{ fontSize: "0.8rem" }}>
                <span className="material-symbols-rounded" style={{ fontSize: 15, marginRight: 4 }}>check_circle</span>
                Approve selection
              </button>
              <button className="btn-primary" type="button" onClick={() => { void handleApply(); }} disabled={isBusy || run.is_stale} style={{ fontSize: "0.8rem" }}>
                <span className="material-symbols-rounded" style={{ fontSize: 15, marginRight: 4 }}>send</span>
                Apply approved
              </button>
            </div>
          </div>
        ) : null}

        {applyResult ? (
          <div className="panel" data-testid="enrichment-apply-result" style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className="material-symbols-rounded" style={{ color: "var(--ok)", fontSize: 20 }}>check_circle</span>
            <p className="muted" style={{ margin: 0 }}>
              Job <strong style={{ color: "var(--text)" }}>#{applyResult.job_id}</strong> queued on <strong style={{ color: "var(--text)" }}>{applyResult.queue}</strong>.
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
