import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { ProductChangeCard } from "@/features/resolution/components/ProductChangeCard";
import { CollaborationBadge } from "@/features/resolution/components/CollaborationBadge";
import { ResolutionProductGroup } from "@/shared/contracts/resolution";

describe("resolution review contract", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders product-grouped review cards with field changes", () => {
    const group: ResolutionProductGroup = {
      item_id: 10,
      product_label: "Ceramic Vase",
      status: "awaiting_approval",
      source_used: "shopify",
      changes: [
        {
          change_id: 1,
          field_group: "pricing",
          field_name: "price",
          before_value: "12.00",
          after_value: "14.50",
          status: "awaiting_approval",
          reason_sentence: "Price updated because supplier catalog changed.",
          reason_factors: { sku_match: true },
          confidence_score: 0.85,
          confidence_badge: "high",
        },
      ],
    };

    const view = render(
      <ProductChangeCard
        group={group}
        readOnly={false}
        selectedIds={new Set()}
        onToggleSelect={vi.fn()}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onEdit={vi.fn()}
      />,
    );

    const card = view.getByTestId("product-group-10");
    expect(within(card).getByText("Ceramic Vase")).toBeInTheDocument();
    expect(within(card).getByText(/Price updated because supplier catalog changed/i)).toBeInTheDocument();
    expect(within(card).getByText(/Confidence:/)).toBeInTheDocument();
  });

  it("disables field actions for read-only users", () => {
    const group: ResolutionProductGroup = {
      item_id: 11,
      product_label: "Read-only Product",
      status: "awaiting_approval",
      changes: [
        {
          change_id: 2,
          field_group: "text",
          field_name: "title",
          before_value: "Old",
          after_value: "New",
          status: "awaiting_approval",
          reason_sentence: "Title normalized.",
          reason_factors: {},
          confidence_score: 0.6,
          confidence_badge: "medium",
        },
      ],
    };

    const view = render(
      <ProductChangeCard
        group={group}
        readOnly
        selectedIds={new Set()}
        onToggleSelect={vi.fn()}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onEdit={vi.fn()}
      />,
    );

    const card = view.getByTestId("product-group-11");
    const approveButton = within(card).getByRole("button", { name: "Approve" });
    expect(approveButton).toBeDisabled();
  });

  it("shows lock ownership and read-only collaboration badge", () => {
    render(<CollaborationBadge locked lockOwnerUserId={22} readOnly />);
    expect(screen.getByTestId("collaboration-badge")).toHaveTextContent(
      "User 22 is currently reviewing this. You are in read-only mode.",
    );
  });

  it("allows checkbox-based field selection for bulk actions", () => {
    const onToggle = vi.fn();
    const group: ResolutionProductGroup = {
      item_id: 12,
      product_label: "Bulk Product",
      status: "awaiting_approval",
      changes: [
        {
          change_id: 3,
          field_group: "ids",
          field_name: "sku",
          before_value: "A-1",
          after_value: "A-2",
          status: "awaiting_approval",
          reason_sentence: "Supplier SKU changed.",
          reason_factors: {},
          confidence_score: 0.7,
          confidence_badge: "medium",
        },
      ],
    };

    const view = render(
      <ProductChangeCard
        group={group}
        readOnly={false}
        selectedIds={new Set()}
        onToggleSelect={onToggle}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onEdit={vi.fn()}
      />,
    );

    const card = view.getByTestId("product-group-12");
    fireEvent.click(within(card).getByRole("checkbox"));
    expect(onToggle).toHaveBeenCalledWith(3, true);
  });
});
