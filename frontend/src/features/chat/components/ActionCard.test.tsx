import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ActionCard } from "@/features/chat/components/ActionCard";
import { ChatAction } from "@/shared/contracts/chat";

function buildAction(overrides: Partial<ChatAction> = {}): ChatAction {
  return {
    id: 11,
    session_id: 3,
    user_id: 1,
    action_type: "update_product",
    status: "approved",
    payload: { dry_run_required: true, preview: {} },
    ...overrides,
  };
}

describe("ActionCard", () => {
  it("calls approve and apply handlers", async () => {
    const onApprove = vi.fn().mockResolvedValue(undefined);
    const onApply = vi.fn().mockResolvedValue(undefined);
    const action = buildAction();

    render(
      <ActionCard
        action={action}
        onApprove={onApprove}
        onApply={onApply}
      />,
    );

    fireEvent.change(screen.getByLabelText("approval comment"), {
      target: { value: "looks good" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    await waitFor(() => {
      expect(onApprove).toHaveBeenCalledWith(11, "looks good");
      expect(onApply).toHaveBeenCalledWith(11);
    });
  });

  it("renders conflict warning for user-decision-required actions", () => {
    const action = buildAction({
      status: "dry_run_ready",
      payload: {
        requires_user_decision: true,
        preview: {
          conflict_item_ids: [100],
        },
      },
    });

    render(
      <ActionCard
        action={action}
        onApprove={() => Promise.resolve()}
        onApply={() => Promise.resolve()}
      />,
    );

    expect(screen.getByTestId("action-warning")).toHaveTextContent("Structural conflicts detected");
  });
});
