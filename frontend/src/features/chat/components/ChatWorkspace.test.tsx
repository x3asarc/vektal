import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ChatWorkspace } from "@/features/chat/components/ChatWorkspace";
import type { ChatUiMessage } from "@/features/chat/hooks/useChatSession";
import type { ChatAction, ChatSession } from "@/shared/contracts/chat";

type ChatWorkspaceHookState = {
  sessions: ChatSession[];
  session: ChatSession | null;
  messages: ChatUiMessage[];
  actions: ChatAction[];
  loading: boolean;
  submitting: boolean;
  error: string | null;
  streamMode: "sse" | "polling" | "degraded";
  streamDegraded: boolean;
  streamError: string | null;
  sendMessage: (content: string) => Promise<void>;
  createBulkAction: (input: {
    content: string;
    skus: string[];
    operation?: "add_product" | "update_product";
    mode?: "immediate" | "scheduled";
    actionHints?: Record<string, unknown>;
  }) => Promise<void>;
  approveAction: (actionId: number, comment?: string) => Promise<void>;
  applyAction: (actionId: number, mode?: "immediate" | "scheduled") => Promise<void>;
  delegateAction: (
    actionId: number,
    input?: { requestedTools?: string[]; depth?: number; fanOut?: number },
  ) => Promise<void>;
  refresh: () => Promise<void>;
};

const useChatSessionMock = vi.fn<() => ChatWorkspaceHookState>();
const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/features/chat/hooks/useChatSession", () => ({
  useChatSession: () => useChatSessionMock(),
}));

describe("ChatWorkspace", () => {
  const baseState: ChatWorkspaceHookState = {
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
    delegateAction: vi.fn().mockResolvedValue(undefined),
    refresh: vi.fn().mockResolvedValue(undefined),
  };

  beforeEach(() => {
    replaceMock.mockReset();
    useChatSessionMock.mockReset();
    useChatSessionMock.mockReturnValue({ ...baseState });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders session state, timeline, and action controls", () => {
    render(<ChatWorkspace />);

    expect(screen.getByRole("heading", { name: /ai assistant/i })).toBeInTheDocument();
    expect(screen.getByText(/State:/)).toHaveTextContent("in_house");
    expect(screen.getByTestId("chat-timeline")).toBeInTheDocument();
    expect(screen.getByTestId("chat-actions")).toBeInTheDocument();
    expect(screen.getByTestId("action-card")).toBeInTheDocument();
  });

  it("does not duplicate assistant text when text block matches content", () => {
    render(<ChatWorkspace />);
    const matches = screen.getAllByText("Prepared dry-run.");
    expect(matches).toHaveLength(1);
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

    fireEvent.change(screen.getByPlaceholderText(/describe a sku update/i), {
      target: { value: "update SKU-100" },
    });
    fireEvent.click(screen.getByTitle("Send"));

    await waitFor(() => {
      expect(sendMessage).toHaveBeenCalledWith("update SKU-100");
    });
  });

  it("renders fallback notice when route telemetry indicates safe fallback", () => {
    useChatSessionMock.mockReturnValue({
      ...baseState,
      messages: [
        {
          id: 201,
          session_id: 5,
          user_id: 1,
          role: "assistant",
          content: "Need clarification",
          blocks: [{ type: "text", text: "Need clarification" }],
          source_metadata: {
            route_summary: {
              fallback_stage: "safe_tier_fallback",
              suggested_escalation: "tier_2",
            },
          },
        },
      ],
    });

    render(<ChatWorkspace />);
    expect(screen.getByTestId("safe-tier-fallback")).toHaveTextContent("safe_tier_fallback");
    expect(screen.getByTestId("safe-tier-fallback")).toHaveTextContent("tier_2");
  });
});
