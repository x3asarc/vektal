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
    <section className="panel" data-testid="enrichment-workspace">
      <h1>enrichment</h1>
      <p className="muted">
        Governed product enrichment with dry-run TTL, policy lineage, and queue-backed apply.
      </p>
      <EnrichmentRunConfigurator onStart={handleStart} isSubmitting={isBusy} />

      {run ? (
        <section className="panel" style={{ marginTop: 12 }} data-testid="enrichment-run-summary">
          <h2>Run Summary</h2>
          <p className="muted">
            Run #{run.run_id} | Profile: <strong>{run.run_profile}</strong> | Language:{" "}
            <strong>{run.target_language}</strong>
          </p>
          <p className="muted">
            Status: <strong>{run.status}</strong> | Oracle: <strong>{run.oracle_decision}</strong> | TTL stale:{" "}
            <strong>{run.is_stale ? "yes" : "no"}</strong>
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" onClick={handleRefresh} disabled={isBusy}>
              Refresh review
            </button>
            <button type="button" onClick={handleApprove} disabled={isBusy || run.is_stale}>
              Approve selection
            </button>
            <button type="button" onClick={handleApply} disabled={isBusy || run.is_stale}>
              Apply approved
            </button>
          </div>
          <p className="muted">
            Counts: allowed {run.write_plan.counts.allowed}, blocked {run.write_plan.counts.blocked}, approved{" "}
            {run.write_plan.counts.approved ?? 0}, total {run.write_plan.counts.total}
          </p>
        </section>
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

      {applyResult ? (
        <section className="panel" data-testid="enrichment-apply-result">
          <h2>Apply queued</h2>
          <p className="muted">
            Job #{applyResult.job_id} queued on <strong>{applyResult.queue}</strong>.
          </p>
        </section>
      ) : null}

      {error ? <p style={{ color: "var(--error)" }}>{error}</p> : null}
    </section>
  );
}
