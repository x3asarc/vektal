"use client";

import { useMemo, useState } from "react";
import { ChatAction } from "@/shared/contracts/chat";
import { BulkRunPanel } from "@/features/chat/components/BulkRunPanel";

type ActionCardProps = {
  action: ChatAction;
  submitting?: boolean;
  onApprove: (actionId: number, comment?: string) => Promise<void> | void;
  onApply: (actionId: number, mode?: "immediate" | "scheduled") => Promise<void> | void;
};

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object") return value as Record<string, unknown>;
  return {};
}

function asNumberArray(value: unknown): number[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is number => typeof item === "number" && Number.isFinite(item));
}

export function ActionCard({ action, submitting = false, onApprove, onApply }: ActionCardProps) {
  const [comment, setComment] = useState("");
  const payload = asRecord(action.payload);
  const isBulk = payload.bulk === true;
  const preview = asRecord(payload.preview);
  const conflictItemIds = asNumberArray(preview.conflict_item_ids);
  const lowConfidenceChangeIds = asNumberArray(preview.low_confidence_change_ids);
  const requiresDecision = payload.requires_user_decision === true || conflictItemIds.length > 0 || lowConfidenceChangeIds.length > 0;
  const canApprove = action.status === "dry_run_ready" || action.status === "awaiting_approval" || action.status === "approved";
  const canApply = action.status === "approved";

  const warningText = useMemo(() => {
    if (!requiresDecision) return null;
    if (conflictItemIds.length > 0) {
      return "Structural conflicts detected. Review before apply.";
    }
    if (lowConfidenceChangeIds.length > 0) {
      return "Low-confidence changes detected. User decision required.";
    }
    return "User decision required before apply.";
  }, [conflictItemIds.length, lowConfidenceChangeIds.length, requiresDecision]);

  return (
    <section className="panel chat-action-card" data-testid="action-card">
      <header className="chat-action-card-header">
        <h3>
          Action #{action.id} <span className="muted">({action.action_type})</span>
        </h3>
        <span className="chat-action-status">{action.status}</span>
      </header>
      <p className="muted">
        Dry-run preview is mandatory before apply. Approve at product scope, then apply.
      </p>
      {warningText && (
        <p className="chat-action-warning" data-testid="action-warning">
          {warningText}
        </p>
      )}
      <div className="chat-action-controls">
        <input
          aria-label="approval comment"
          placeholder="Optional approval comment"
          value={comment}
          onChange={(event) => setComment(event.target.value)}
        />
        <button
          type="button"
          disabled={!canApprove || submitting}
          onClick={() => void onApprove(action.id, comment || undefined)}
        >
          {submitting ? "Approving..." : "Approve"}
        </button>
        <button
          type="button"
          disabled={!canApply || submitting}
          onClick={() => void onApply(action.id)}
        >
          {submitting ? "Applying..." : "Apply"}
        </button>
      </div>
      {isBulk && <BulkRunPanel action={action} />}
      {!isBulk && action.result && (
        <pre className="chat-action-result">{JSON.stringify(action.result, null, 2)}</pre>
      )}
    </section>
  );
}
