"use client";

import { ChatAction } from "@/shared/contracts/chat";

type BulkRunPanelProps = {
  action: ChatAction;
};

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object") {
    return value as Record<string, unknown>;
  }
  return {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

export function BulkRunPanel({ action }: BulkRunPanelProps) {
  const payload = asRecord(action.payload);
  const chunkPlan = asRecord(payload.chunk_plan);
  const chunkResults = asRecord(payload.chunk_results);
  const summary = asRecord(asRecord(payload.bulk_summary));
  const result = asRecord(action.result);

  const chunks = asArray(chunkPlan.chunks);
  const totalSkus = asNumber(chunkPlan.total_skus);
  const chunkCount = asNumber(chunkPlan.chunk_count) || chunks.length;
  const applied = asNumber(summary.applied);
  const conflicted = asNumber(summary.conflicted);
  const failed = asNumber(summary.failed);
  const skipped = asNumber(summary.skipped);
  const jobId = asNumber(result.job_id);
  const recoveryLogIds = asArray(summary.recovery_log_ids);

  return (
    <section className="panel chat-bulk-panel" data-testid="bulk-run-panel">
      <h3 className="forensic-card-title">Bulk Run</h3>
      <p className="forensic-card-copy">
        {totalSkus} SKU(s) across {chunkCount} chunk(s). Status: <strong>{action.status}</strong>
      </p>
      <div className="chat-bulk-summary">
        <span>Applied: {applied}</span>
        <span>Conflicted: {conflicted}</span>
        <span>Failed: {failed}</span>
        <span>Skipped: {skipped}</span>
      </div>
      {jobId > 0 && (
        <p className="muted">
          <a href={`/jobs/${jobId}`}>View job #{jobId}</a>
        </p>
      )}
      {recoveryLogIds.length > 0 && (
        <p className="muted">
          Recovery logs: {recoveryLogIds.map((id) => String(id)).join(", ")}
        </p>
      )}
      <div className="chat-bulk-chunks">
        {Object.entries(chunkResults).map(([chunkId, value]) => {
          const row = asRecord(value);
          const status = typeof row.status === "string" ? row.status : "unknown";
          const rowApplied = asNumber(row.applied_count);
          const rowFailed = asNumber(row.failed_count);
          const rowConflicted = asNumber(row.conflicted_count);
          return (
            <div key={chunkId} className="chat-bulk-chunk" data-chunk-status={status}>
              <strong>{chunkId}</strong>
              <span className="forensic-state-tag" data-state={status === "completed" ? "ok" : status === "blocked" ? "blocked" : "warning"}>
                {status}
              </span>
              <span>A:{rowApplied}</span>
              <span>C:{rowConflicted}</span>
              <span>F:{rowFailed}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
