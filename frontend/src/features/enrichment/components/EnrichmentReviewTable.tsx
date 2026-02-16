"use client";

import { EnrichmentDecisionRow } from "@/features/enrichment/api/enrichment-api";

type EnrichmentReviewTableProps = {
  rows: EnrichmentDecisionRow[];
  selectedIds: Set<number>;
  onToggle: (itemId: number) => void;
};

function renderValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function EnrichmentReviewTable({ rows, selectedIds, onToggle }: EnrichmentReviewTableProps) {
  return (
    <section className="panel" data-testid="enrichment-review-table">
      <h2>Before / After Review</h2>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: 8 }}>Select</th>
              <th style={{ textAlign: "left", padding: 8 }}>Product</th>
              <th style={{ textAlign: "left", padding: 8 }}>Field</th>
              <th style={{ textAlign: "left", padding: 8 }}>Before</th>
              <th style={{ textAlign: "left", padding: 8 }}>After</th>
              <th style={{ textAlign: "left", padding: 8 }}>Confidence</th>
              <th style={{ textAlign: "left", padding: 8 }}>Reason codes</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: 8 }}>
                  No enrichment items in this run.
                </td>
              </tr>
            ) : (
              rows.map((row) => {
                const itemId = Number(row.item_id ?? -1);
                const canSelect = !row.is_blocked && itemId > 0;
                return (
                  <tr key={`${row.product_id}-${row.field_name}-${itemId}`}>
                    <td style={{ borderTop: "1px solid var(--border)", padding: 8 }}>
                      <input
                        type="checkbox"
                        aria-label={`Select enrichment item ${itemId}`}
                        disabled={!canSelect}
                        checked={canSelect ? selectedIds.has(itemId) : false}
                        onChange={() => {
                          if (canSelect) onToggle(itemId);
                        }}
                      />
                    </td>
                    <td style={{ borderTop: "1px solid var(--border)", padding: 8 }}>{row.product_id ?? "-"}</td>
                    <td style={{ borderTop: "1px solid var(--border)", padding: 8 }}>
                      {row.field_name}
                      {row.is_blocked ? (
                        <span style={{ marginLeft: 6, color: "var(--warning)" }}>(blocked)</span>
                      ) : null}
                    </td>
                    <td style={{ borderTop: "1px solid var(--border)", padding: 8 }}>{renderValue(row.before_value)}</td>
                    <td style={{ borderTop: "1px solid var(--border)", padding: 8 }}>{renderValue(row.after_value)}</td>
                    <td style={{ borderTop: "1px solid var(--border)", padding: 8 }}>
                      {row.confidence === null || row.confidence === undefined ? "-" : row.confidence.toFixed(2)}
                    </td>
                    <td style={{ borderTop: "1px solid var(--border)", padding: 8 }}>
                      {row.reason_codes.length ? row.reason_codes.join(", ") : "-"}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
