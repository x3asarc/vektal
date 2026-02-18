"use client";

import { useEffect, useMemo, useState } from "react";
import { ApiClientError } from "@/lib/api/client";
import { fetchDryRunLineage } from "@/features/resolution/api/resolution-api";
import { ProductChangeCard } from "@/features/resolution/components/ProductChangeCard";
import { CollaborationBadge } from "@/features/resolution/components/CollaborationBadge";
import { useResolutionReviewStore } from "@/features/resolution/state/review-store";
import { ResolutionLineageEntry } from "@/shared/contracts/resolution";

type DryRunReviewProps = {
  batchId?: number;
};

export function DryRunReview({ batchId }: DryRunReviewProps) {
  const {
    batch,
    loading,
    lockError,
    hydrate,
    acquire,
    release,
    startHeartbeat,
    stopHeartbeat,
  } = useResolutionReviewStore();
  const [selectedChangeIds, setSelectedChangeIds] = useState<Set<number>>(new Set());
  const [lineage, setLineage] = useState<ResolutionLineageEntry[]>([]);
  const [lineageError, setLineageError] = useState<string | null>(null);

  useEffect(() => {
    if (!batchId) return;
    void hydrate(batchId);
  }, [batchId, hydrate]);

  useEffect(() => {
    if (!batchId) return;
    void fetchDryRunLineage(batchId)
      .then((entries) => setLineage(entries))
      .catch((error: unknown) => {
        if (error instanceof ApiClientError) {
          setLineageError(error.normalized.detail);
          return;
        }
        setLineageError("Unable to load lineage details.");
      });
  }, [batchId]);

  useEffect(() => {
    return () => stopHeartbeat();
  }, [stopHeartbeat]);

  const totalChanges = useMemo(() => {
    if (!batch) return 0;
    return batch.groups.reduce((sum, group) => sum + group.changes.length, 0);
  }, [batch]);

  function toggleSelect(changeId: number, checked: boolean) {
    setSelectedChangeIds((previous) => {
      const next = new Set(previous);
      if (checked) next.add(changeId);
      else next.delete(changeId);
      return next;
    });
  }

  function updateLocalChange(changeId: number, update: Partial<{ status: string; after_value: string }>) {
    if (!batch) return;
    const groups = batch.groups.map((group) => ({
      ...group,
      changes: group.changes.map((change) =>
        change.change_id === changeId
          ? {
              ...change,
              status: (update.status as typeof change.status | undefined) ?? change.status,
              after_value: update.after_value ?? change.after_value,
            }
          : change,
      ),
    }));
    useResolutionReviewStore.setState({ batch: { ...batch, groups } });
  }

  function bulkApproveSelected() {
    for (const changeId of selectedChangeIds) {
      updateLocalChange(changeId, { status: "approved" });
    }
  }

  if (!batchId) {
    return (
      <section className="panel">
        <h2>Dry-Run Review</h2>
        <p className="muted">Pass a batch id to review a dry-run.</p>
      </section>
    );
  }

  return (
    <section className="panel" style={{ display: "grid", gap: 16 }}>
      <header style={{ display: "grid", gap: 8 }}>
        <h2 style={{ margin: 0 }}>Dry-Run Review</h2>
        <p className="muted" style={{ margin: 0 }}>
          Product-grouped review with per-field controls and explainability.
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={() => {
              void acquire(batchId).then(() => startHeartbeat(batchId));
            }}
          >
            Acquire checkout lock
          </button>
          <button type="button" onClick={() => void release(batchId)}>
            Release checkout lock
          </button>
          <button type="button" onClick={bulkApproveSelected} disabled={selectedChangeIds.size === 0}>
            Approve selected fields
          </button>
        </div>
        <CollaborationBadge
          locked={Boolean(batch?.lock_owner_user_id)}
          lockOwnerUserId={batch?.lock_owner_user_id}
          readOnly={batch?.read_only ?? false}
        />
        {lockError && <p style={{ color: "var(--error)", margin: 0 }}>{lockError}</p>}
      </header>

      {loading && <p className="muted">Loading dry-run...</p>}

      {batch && (
        <>
          <p className="muted" style={{ margin: 0 }}>
            Batch #{batch.batch_id} • {batch.status} • {totalChanges} field changes
          </p>
          <div style={{ display: "grid", gap: 12 }}>
            {batch.groups.map((group) => (
              <ProductChangeCard
                key={group.item_id}
                group={group}
                readOnly={batch.read_only}
                selectedIds={selectedChangeIds}
                onToggleSelect={toggleSelect}
                onApprove={(changeId) => updateLocalChange(changeId, { status: "approved" })}
                onReject={(changeId) => updateLocalChange(changeId, { status: "rejected" })}
                onEdit={(changeId, value) => updateLocalChange(changeId, { after_value: value })}
              />
            ))}
          </div>
          <section className="panel" style={{ display: "grid", gap: 6 }}>
            <h3 style={{ margin: 0 }}>Why changed?</h3>
            {lineageError ? (
              <p className="muted">{lineageError}</p>
            ) : (
              <ul style={{ margin: 0 }}>
                {lineage.slice(0, 5).map((entry) => (
                  <li key={`${entry.item_id}-${entry.change_id}`}>
                    {entry.field_name}: {entry.reason_sentence ?? "No lineage detail"}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </section>
  );
}
