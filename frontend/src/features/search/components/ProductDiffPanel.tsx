"use client";

type DiffRow = {
  field: string;
  before: unknown;
  after: unknown;
  altTextState?: "preserved" | "candidate" | "approved_overwrite";
};

type ProductDiffPanelProps = {
  rows: DiffRow[];
};

function asText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function ProductDiffPanel({ rows }: ProductDiffPanelProps) {
  return (
    <section className="panel" data-testid="product-diff-panel">
      <h2>Side-by-Side Diff</h2>
      <p className="muted">Review before/after values before approval.</p>
      {rows.length === 0 ? (
        <p className="muted">No pending diff rows.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: 8 }}>Field</th>
              <th style={{ textAlign: "left", padding: 8 }}>Before</th>
              <th style={{ textAlign: "left", padding: 8 }}>After</th>
              <th style={{ textAlign: "left", padding: 8 }}>Policy</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.field}>
                <td style={{ borderTop: "1px solid var(--border)", padding: 8 }}>{row.field}</td>
                <td style={{ borderTop: "1px solid var(--border)", padding: 8 }}>{asText(row.before)}</td>
                <td style={{ borderTop: "1px solid var(--border)", padding: 8 }}>{asText(row.after)}</td>
                <td style={{ borderTop: "1px solid var(--border)", padding: 8 }}>
                  {row.altTextState ? (
                    <span data-alt-text-state={row.altTextState}>{row.altTextState}</span>
                  ) : (
                    <span className="muted">n/a</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
