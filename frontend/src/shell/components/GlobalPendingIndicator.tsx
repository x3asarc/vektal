"use client";

import { usePendingStore } from "@/shell/state/pending-store";

export function GlobalPendingIndicator() {
  const pendingCount = usePendingStore((state) => state.pendingCount);
  if (pendingCount === 0) return null;

  return (
    <div className="panel" role="status" aria-live="polite">
      <strong>submitting</strong>
      <p className="muted">
        Critical writes are ack-first. {pendingCount} action(s) awaiting backend
        acknowledgment.
      </p>
    </div>
  );
}
