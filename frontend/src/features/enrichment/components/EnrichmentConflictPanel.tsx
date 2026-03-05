"use client";

import { EnrichmentDecisionRow } from "@/features/enrichment/api/enrichment-api";

type EnrichmentConflictPanelProps = {
  blockedRows: EnrichmentDecisionRow[];
  protectedColumns: string[];
};

export function EnrichmentConflictPanel({ blockedRows, protectedColumns }: EnrichmentConflictPanelProps) {
  return (
    <section className="panel" data-testid="enrichment-conflict-panel">
      <h2 className="forensic-card-title">Blocked Fields & Policy Guidance</h2>
      <p className="forensic-card-copy">
        Protected columns: {protectedColumns.length ? protectedColumns.join(", ") : "none"}
      </p>
      {blockedRows.length === 0 ? (
        <p className="forensic-card-copy">No blocked fields in this run.</p>
      ) : (
        <ul className="enrichment-conflict-list">
          {blockedRows.map((row) => (
            <li key={`${row.product_id}-${row.field_name}-${row.item_id ?? "blocked"}`}>
              <strong>{row.field_name}</strong>: {row.reason_codes.join(", ")}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
