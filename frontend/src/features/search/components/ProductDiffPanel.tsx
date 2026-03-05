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

export function ProductDiffPanel({ rows }: ProductDiffPanelProps) {
  return (
    <section className="panel" data-testid="product-diff-panel">
      <h2 className="forensic-card-title">Side-by-Side Diff</h2>
      <p className="forensic-card-copy">Review before/after values before approval.</p>
      {rows.length === 0 ? (
        <p className="forensic-card-copy">No pending diff rows.</p>
      ) : (
        <div className="forensic-table-wrap">
          <table className="forensic-table">
          <thead>
            <tr>
              <th>Field</th>
              <th>Before</th>
              <th>After</th>
              <th>Policy</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.field}>
                <td>{row.field}</td>
                <td>{asText(row.before)}</td>
                <td>{asText(row.after)}</td>
                <td>
                  {row.altTextState ? (
                    <span className="diff-state-chip" data-alt-text-state={row.altTextState}>{row.altTextState}</span>
                  ) : (
                    <span className="muted">n/a</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </section>
  );
}
