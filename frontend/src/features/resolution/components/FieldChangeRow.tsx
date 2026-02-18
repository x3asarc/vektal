"use client";

import { ResolutionChange } from "@/shared/contracts/resolution";
import { TechnicalDetailsToggle } from "@/features/resolution/components/TechnicalDetailsToggle";

type FieldChangeRowProps = {
  change: ResolutionChange;
  selected: boolean;
  readOnly: boolean;
  onSelect: (checked: boolean) => void;
  onApprove: () => void;
  onReject: () => void;
  onEdit: (value: string) => void;
};

function statusTone(status: ResolutionChange["status"]) {
  switch (status) {
    case "auto_applied":
      return "var(--ok)";
    case "blocked_exclusion":
      return "var(--warning)";
    case "structural_conflict":
      return "var(--error)";
    default:
      return "var(--accent)";
  }
}

function toText(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

export function FieldChangeRow({
  change,
  selected,
  readOnly,
  onSelect,
  onApprove,
  onReject,
  onEdit,
}: FieldChangeRowProps) {
  const isEditable = !readOnly && change.status !== "auto_applied";
  const badge = change.confidence_badge ?? "n/a";

  return (
    <article
      className="panel"
      style={{
        display: "grid",
        gap: 8,
        borderLeft: `4px solid ${statusTone(change.status)}`,
      }}
      data-testid={`field-change-${change.change_id}`}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            checked={selected}
            disabled={readOnly}
            onChange={(event) => onSelect(event.currentTarget.checked)}
          />
          <strong>{change.field_name}</strong>
        </label>
        <span data-testid={`change-status-${change.change_id}`}>{change.status}</span>
      </div>
      <p className="muted">{change.reason_sentence ?? "No reason available."}</p>
      <div style={{ display: "grid", gap: 4 }}>
        <div>
          <strong>Before:</strong> {toText(change.before_value) || "(empty)"}
        </div>
        <div>
          <strong>After:</strong> {toText(change.after_value) || "(empty)"}
        </div>
        <div>
          <strong>Confidence:</strong>{" "}
          {typeof change.confidence_score === "number"
            ? `${Math.round(change.confidence_score * 100)}%`
            : "N/A"}{" "}
          ({badge})
        </div>
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button type="button" onClick={onApprove} disabled={!isEditable}>
          Approve
        </button>
        <button type="button" onClick={onReject} disabled={!isEditable}>
          Reject
        </button>
        <button
          type="button"
          onClick={() => onEdit(String(change.after_value ?? ""))}
          disabled={!isEditable}
        >
          Edit value
        </button>
      </div>
      <TechnicalDetailsToggle summary="technical details">
        <pre style={{ margin: 0, overflowX: "auto" }}>
          {JSON.stringify(change.reason_factors, null, 2)}
        </pre>
      </TechnicalDetailsToggle>
    </article>
  );
}
