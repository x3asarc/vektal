import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ActionCard } from "@/features/chat/components/ActionCard";
import { ChatAction } from "@/shared/contracts/chat";

vi.mock("@/features/resolution/components/DryRunReview", () => ({
  DryRunReview: ({ batchId }: { batchId?: number }) => (
    <div data-testid="dry-run-review">dry-run-review-{batchId ?? "none"}</div>
  ),
}));

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
    const onDelegate = vi.fn().mockResolvedValue(undefined);
    const action = buildAction();

    render(
      <ActionCard
        action={action}
        onApprove={onApprove}
        onApply={onApply}
        onDelegate={onDelegate}
      />,
    );

    fireEvent.change(screen.getByLabelText("approval comment"), {
      target: { value: "looks good" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    fireEvent.click(screen.getByRole("button", { name: "Delegate" }));

    await waitFor(() => {
      expect(onApprove).toHaveBeenCalledWith(11, "looks good");
      expect(onApply).toHaveBeenCalledWith(11);
      expect(onDelegate).toHaveBeenCalledWith(11);
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

  it("renders delegation trace panel when trace exists", () => {
    const action = buildAction({
      payload: {
        preview: {},
        delegation_trace: {
          delegation_event_id: 9,
          status: "running",
          worker_tool_scope: ["chat.respond"],
          blocked_tools: [],
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
    expect(screen.getByTestId("delegation-trace")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /View Trace/i }));
    expect(screen.getByText(/delegation_event_id/i)).toBeInTheDocument();
  });

  it("renders dry-run review when dry_run_id is present", () => {
    const action = buildAction({
      payload: {
        dry_run_id: 42,
        preview: {},
      },
    });

    render(
      <ActionCard
        action={action}
        onApprove={() => Promise.resolve()}
        onApply={() => Promise.resolve()}
      />,
    );

    expect(screen.getByText(/Open dry-run review/i)).toBeInTheDocument();
    expect(screen.getByTestId("dry-run-review")).toHaveTextContent("dry-run-review-42");
  });
});
