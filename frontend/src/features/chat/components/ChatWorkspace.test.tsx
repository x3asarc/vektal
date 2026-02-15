import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ChatWorkspace } from "@/features/chat/components/ChatWorkspace";

const useChatSessionMock = vi.fn();

vi.mock("@/features/chat/hooks/useChatSession", () => ({
  useChatSession: (...args: unknown[]) => useChatSessionMock(...args),
}));

describe("ChatWorkspace", () => {
  const baseState = {
    sessions: [{ id: 5, user_id: 1, title: "Chat Workspace", state: "in_house", status: "active" }],
    session: { id: 5, user_id: 1, title: "Chat Workspace", state: "in_house", status: "active" },
    messages: [
      {
        id: 100,
        session_id: 5,
        user_id: 1,
        role: "assistant",
        content: "Prepared dry-run.",
        blocks: [{ type: "text", text: "Prepared dry-run." }],
      },
    ],
    actions: [
      {
        id: 8,
        session_id: 5,
        user_id: 1,
        action_type: "update_product",
        status: "approved",
        payload: { dry_run_required: true, preview: {} },
        result: null,
      },
    ],
    loading: false,
    submitting: false,
    error: null,
    streamMode: "sse",
    streamDegraded: false,
    streamError: null,
    sendMessage: vi.fn().mockResolvedValue(undefined),
    createBulkAction: vi.fn().mockResolvedValue(undefined),
    approveAction: vi.fn().mockResolvedValue(undefined),
    applyAction: vi.fn().mockResolvedValue(undefined),
    refresh: vi.fn().mockResolvedValue(undefined),
  };

  beforeEach(() => {
    useChatSessionMock.mockReset();
    useChatSessionMock.mockReturnValue({ ...baseState });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders session state, timeline, and action controls", () => {
    render(<ChatWorkspace />);

    expect(screen.getByText("chat")).toBeInTheDocument();
    expect(screen.getByText(/Context state:/)).toHaveTextContent("in_house");
    expect(screen.getByTestId("chat-timeline")).toBeInTheDocument();
    expect(screen.getByTestId("chat-actions")).toBeInTheDocument();
    expect(screen.getByTestId("action-card")).toBeInTheDocument();
  });

  it("submits a chat message from composer", async () => {
    const sendMessage = vi.fn().mockResolvedValue(undefined);
    useChatSessionMock.mockReturnValue({
      ...baseState,
      sendMessage,
      actions: [],
      messages: [],
    });
    render(<ChatWorkspace />);

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "update SKU-100" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => {
      expect(sendMessage).toHaveBeenCalledWith("update SKU-100");
    });
  });
});
