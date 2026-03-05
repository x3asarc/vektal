import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import JobDetailPage from "@/app/(app)/jobs/[id]/page";
import type { JobDetail } from "@/features/jobs/hooks/useJobDetailObserver";

const {
  apiRequestMock,
  useJobDetailObserverMock,
} = vi.hoisted(() => ({
  apiRequestMock: vi.fn<(...args: unknown[]) => Promise<unknown>>(),
  useJobDetailObserverMock: vi.fn<() => JobObserverResult>(),
}));

type JobObserverResult = {
  mode: "sse" | "polling" | "degraded";
  degraded: boolean;
  error: string | null;
  job: JobDetail | null;
  events: Array<{ id: string; at: string; kind: "sse" | "poll" | "transport" | "error"; message: string }>;
  pollNow: () => Promise<void>;
  reconnect: () => void;
};
const locationAssignMock = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "77" }),
}));

vi.mock("@/features/jobs/hooks/useJobDetailObserver", () => ({
  useJobDetailObserver: useJobDetailObserverMock,
}));

vi.mock("@/lib/api/client", () => ({
  apiRequest: (...args: unknown[]) => apiRequestMock(...args),
  ApiClientError: class ApiClientError extends Error {
    normalized: { detail: string; status: number };

    constructor(normalized: { detail: string; status: number }) {
      super(normalized.detail);
      this.normalized = normalized;
    }
  },
}));

describe("JobDetailPage", () => {
  beforeEach(() => {
    apiRequestMock.mockReset();
    useJobDetailObserverMock.mockReset();
    useJobDetailObserverMock.mockReturnValue({
      mode: "sse",
      degraded: false,
      error: null,
      events: [],
      pollNow: vi.fn(async () => {}),
      reconnect: vi.fn(),
      job: {
        id: 77,
        status: "failed_terminal",
        percent_complete: 100,
        current_step_label: "Failed",
        eta_seconds: null,
        processed_items: 100,
        total_items: 100,
        error_message: "strict_failed_chunk",
        can_retry: true,
        results_url: "/jobs/77?tab=results",
      },
    });
    locationAssignMock.mockReset();
    vi.stubGlobal("location", { assign: locationAssignMock });
  });

  it("renders progress, step, eta fallback, and retry action", async () => {
    render(<JobDetailPage />);

    expect(screen.getByTestId("job-progress-percent")).toHaveTextContent("100.0% complete");
    expect(screen.getByTestId("job-current-step")).toHaveTextContent("Failed");
    expect(screen.getByTestId("job-eta")).toHaveTextContent("Calculating ETA...");
    expect(screen.getByTestId("job-retry-button")).toBeInTheDocument();
    expect(screen.getByText("View results")).toHaveAttribute("href", "/jobs/77?tab=results");

    apiRequestMock.mockResolvedValue({ job_id: 88 });
    fireEvent.click(screen.getByTestId("job-retry-button"));

    await waitFor(() => {
      expect(apiRequestMock).toHaveBeenCalledWith("/api/v1/jobs/77/retry", { method: "POST" });
    });
    await waitFor(() => {
      expect(locationAssignMock).toHaveBeenCalledWith("/jobs/88");
    });
  });
});
