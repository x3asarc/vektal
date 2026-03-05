"use client";

import { EnrichmentDecisionRow } from "@/features/enrichment/api/enrichment-api";

type EnrichmentReviewTableProps = {
  rows: EnrichmentDecisionRow[];
  selectedIds: Set<number>;
  onToggle: (itemId: number) => void;
};

function renderValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (typeof value === "object") {
    try {
      return JSON.stringify(value) ?? "[unserializable]";
    } catch {
      return "[unserializable]";
    }
  }
  return "[unsupported]";
}

export function EnrichmentReviewTable({ rows, selectedIds, onToggle }: EnrichmentReviewTableProps) {
  return (
    <section className="panel" data-testid="enrichment-review-table">
      <h2 className="forensic-card-title">Before / After Review</h2>
      <div className="forensic-table-wrap">
        <table className="forensic-table">
          <thead>
            <tr>
              <th>Select</th>
              <th>Product</th>
              <th>Field</th>
              <th>Before</th>
              <th>After</th>
              <th>Confidence</th>
              <th>Reason codes</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  No enrichment items in this run.
                </td>
              </tr>
            ) : (
              rows.map((row) => {
                const itemId = Number(row.item_id ?? -1);
                const canSelect = !row.is_blocked && itemId > 0;
                return (
                  <tr key={`${row.product_id}-${row.field_name}-${itemId}`}>
                    <td>
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
                    <td>{row.product_id ?? "-"}</td>
                    <td>
                      {row.field_name}
                      {row.is_blocked ? (
                        <span style={{ marginLeft: 6, color: "var(--brand-warning)" }}>(blocked)</span>
                      ) : null}
                    </td>
                    <td>{renderValue(row.before_value)}</td>
                    <td>{renderValue(row.after_value)}</td>
                    <td>
                      {row.confidence === null || row.confidence === undefined ? "-" : row.confidence.toFixed(2)}
                    </td>
                    <td>
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
