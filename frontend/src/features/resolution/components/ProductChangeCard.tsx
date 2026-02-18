"use client";

import { ResolutionProductGroup } from "@/shared/contracts/resolution";
import { FieldChangeRow } from "@/features/resolution/components/FieldChangeRow";

type ProductChangeCardProps = {
  group: ResolutionProductGroup;
  readOnly: boolean;
  selectedIds: Set<number>;
  onToggleSelect: (changeId: number, checked: boolean) => void;
  onApprove: (changeId: number) => void;
  onReject: (changeId: number) => void;
  onEdit: (changeId: number, value: string) => void;
};

export function ProductChangeCard({
  group,
  readOnly,
  selectedIds,
  onToggleSelect,
  onApprove,
  onReject,
  onEdit,
}: ProductChangeCardProps) {
  return (
    <section
      className="panel"
      style={{ display: "grid", gap: 12 }}
      data-testid={`product-group-${group.item_id}`}
    >
      <header style={{ display: "grid", gap: 4 }}>
        <h3 style={{ margin: 0 }}>{group.product_label ?? `Product ${group.item_id}`}</h3>
        <p className="muted" style={{ margin: 0 }}>
          Status: <strong>{group.status}</strong>
          {group.source_used ? ` • Source: ${group.source_used}` : ""}
        </p>
        {group.structural_state && (
          <p style={{ margin: 0 }}>
            <strong>Structural conflict:</strong> {group.structural_state}
          </p>
        )}
        {group.conflict_reason && <p className="muted" style={{ margin: 0 }}>{group.conflict_reason}</p>}
      </header>
      <div style={{ display: "grid", gap: 8 }}>
        {group.changes.map((change) => (
          <FieldChangeRow
            key={change.change_id}
            change={change}
            readOnly={readOnly}
            selected={selectedIds.has(change.change_id)}
            onSelect={(checked) => onToggleSelect(change.change_id, checked)}
            onApprove={() => onApprove(change.change_id)}
            onReject={() => onReject(change.change_id)}
            onEdit={(value) => onEdit(change.change_id, value)}
          />
        ))}
      </div>
    </section>
  );
}
