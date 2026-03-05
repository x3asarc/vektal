import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApprovalQueue } from "@/features/approvals/components/ApprovalQueue";

function buildApproval() {
  return {
    approval_id: "a-123",
    title: "Fix Redis reconnect policy",
    confidence: 0.82,
    blast_radius_files: 2,
    blast_radius_loc: 14,
    created_at: "2026-03-02T12:00:00Z",
    expires_at: "2026-03-05T12:00:00Z",
    type: "code_change",
    status: "pending",
  };
}

describe("ApprovalQueue", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "alert").mockImplementation(() => {});
    vi.spyOn(window, "prompt").mockReturnValue("Not safe yet");
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("loads and renders pending approvals", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ approvals: [buildApproval()] }),
    });

    render(<ApprovalQueue />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/approvals/");
    });
    expect(screen.getByText("Fix Redis reconnect policy")).toBeInTheDocument();
    expect(screen.getByText("low")).toBeInTheDocument();
    expect(screen.getByText("14")).toBeInTheDocument();
  });

  it("approves an item and removes it from the list", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ approvals: [buildApproval()] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: "approved" }),
      });

    render(<ApprovalQueue />);
    await screen.findByText("Fix Redis reconnect policy");

    fireEvent.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/approvals/a-123/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
    });
    await waitFor(() => {
      expect(screen.queryByText("Fix Redis reconnect policy")).not.toBeInTheDocument();
    });
  });

  it("rejects an item and removes it from the list", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ approvals: [buildApproval()] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: "rejected" }),
      });

    render(<ApprovalQueue />);
    await screen.findByText("Fix Redis reconnect policy");

    fireEvent.click(screen.getByRole("button", { name: "Reject" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/v1/approvals/a-123/reject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note: "Not safe yet" }),
      });
    });
    await waitFor(() => {
      expect(screen.queryByText("Fix Redis reconnect policy")).not.toBeInTheDocument();
    });
  });

  it("shows empty state when queue is empty", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ approvals: [] }),
    });

    render(<ApprovalQueue />);

    expect(await screen.findByText(/No pending approvals/i)).toBeInTheDocument();
  });
});
