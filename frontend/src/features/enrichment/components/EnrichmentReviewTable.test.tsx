import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EnrichmentDecisionRow } from "@/features/enrichment/api/enrichment-api";
import { EnrichmentReviewTable } from "@/features/enrichment/components/EnrichmentReviewTable";

const rows: EnrichmentDecisionRow[] = [
  {
    item_id: 1,
    product_id: 10,
    field_name: "title",
    field_group: "text",
    before_value: "Old",
    after_value: "New",
    policy_version: 1,
    mapping_version: 1,
    reason_codes: ["allowed"],
    requires_user_action: true,
    is_blocked: false,
    is_protected_column: false,
    alt_text_preserved: true,
    confidence: 0.92,
    provenance: { source: "ai_inferred" },
    decision_state: "suggested",
  },
  {
    item_id: 2,
    product_id: 10,
    field_name: "alt_text",
    field_group: "images",
    before_value: "old alt",
    after_value: "new alt",
    policy_version: 1,
    mapping_version: 1,
    reason_codes: ["alt_text_policy_preserve"],
    requires_user_action: true,
    is_blocked: true,
    is_protected_column: false,
    alt_text_preserved: true,
    confidence: 0.7,
    provenance: { source: "ai_inferred" },
    decision_state: "blocked",
  },
];

describe("EnrichmentReviewTable", () => {
  it("renders rows and toggles selectable items", () => {
    const onToggle = vi.fn();
    render(<EnrichmentReviewTable rows={rows} selectedIds={new Set<number>([1])} onToggle={onToggle} />);

    expect(screen.getByText("Before / After Review")).toBeInTheDocument();
    expect(screen.getByText("alt_text")).toBeInTheDocument();
    expect(screen.getByText("(blocked)")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Select enrichment item 1"));
    expect(onToggle).toHaveBeenCalledWith(1);

    const blockedCheckbox = screen.getByLabelText("Select enrichment item 2");
    expect(blockedCheckbox).toBeDisabled();
  });
});
