import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { OnboardingWizard } from "@/features/onboarding/components/OnboardingWizard";
import type { JobDetail } from "@/lib/jobs/useJobDetailObserver";

const {
  startImportMutateAsyncMock,
  apiRequestMock,
  useJobDetailObserverMock,
} = vi.hoisted(() => ({
  startImportMutateAsyncMock: vi.fn<(...args: unknown[]) => Promise<unknown>>(),
  apiRequestMock: vi.fn<(...args: unknown[]) => Promise<unknown>>(),
  useJobDetailObserverMock: vi.fn<(jobId: number | string | null) => JobObserverResult>(),
}));

type JobObserverResult = {
  mode: "sse" | "polling" | "degraded";
  degraded: boolean;
  error: string | null;
  job: JobDetail | null;
};

vi.mock("@/features/onboarding/state/onboarding-machine", () => ({
  INITIAL_ONBOARDING_STATE: {
    step: "preview_start_import",
    ingestPath: "sync_store",
    advancedOpen: false,
  },
  chooseIngestPath: (state: Record<string, unknown>) => state,
  connectShopify: (state: Record<string, unknown>) => state,
  startImport: (state: Record<string, unknown>) => ({ ...state, step: "import_progress" }),
  markComplete: (state: Record<string, unknown>) => ({ ...state, step: "completed" }),
  toggleAdvanced: (state: Record<string, unknown>) => ({
    ...state,
    advancedOpen: !state.advancedOpen,
  }),
}));

vi.mock("@/features/onboarding/api/onboarding-mutations", () => ({
  useConnectShopifyMutation: () => ({ mutateAsync: vi.fn() }),
  useStartImportMutation: () => ({ mutateAsync: startImportMutateAsyncMock }),
}));

vi.mock("@/lib/jobs/useJobDetailObserver", () => ({
  useJobDetailObserver: useJobDetailObserverMock,
}));

vi.mock("@/lib/auth/session-flags", () => ({
  setGuardFlags: vi.fn(),
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

describe("OnboardingWizard import progress", () => {
  beforeEach(() => {
    startImportMutateAsyncMock.mockReset();
    apiRequestMock.mockReset();
    useJobDetailObserverMock.mockReset();
    useJobDetailObserverMock.mockImplementation((jobId: number | string | null) => ({
      mode: "sse",
      degraded: false,
      error: null,
      job: jobId
        ? {
            id: Number(jobId),
            status: "failed_terminal",
            current_step_label: "Applying updates",
            percent_complete: 55,
            eta_seconds: 42,
            processed_items: 11,
            total_items: 20,
            can_retry: true,
            results_url: "/jobs/77?tab=results",
            error_message: "strict_failed_chunk",
          }
        : null,
    }));
  });

  it("binds live job data and retry controls to import progress view", async () => {
    startImportMutateAsyncMock.mockResolvedValue({ job_id: 77, status: "queued" });

    render(<OnboardingWizard />);

    fireEvent.click(screen.getByRole("button", { name: "Preview and Start Import" }));

    await waitFor(() => {
      expect(screen.getByText("Import in progress. You can navigate away without blocking.")).toBeInTheDocument();
    });
    expect(screen.getByText("55.0% complete")).toBeInTheDocument();
    expect(screen.getByText("Applying updates")).toBeInTheDocument();
    expect(screen.getByText("42s")).toBeInTheDocument();
    expect(screen.getByText("11")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry import" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View results" })).toHaveAttribute(
      "href",
      "/jobs/77?tab=results",
    );
    expect(screen.getByRole("link", { name: "Open job detail" })).toHaveAttribute(
      "href",
      "/jobs/77",
    );

    apiRequestMock.mockResolvedValue({ job_id: 88 });
    fireEvent.click(screen.getByRole("button", { name: "Retry import" }));

    await waitFor(() => {
      expect(apiRequestMock).toHaveBeenCalledWith("/api/v1/jobs/77/retry", {
        method: "POST",
      });
    });
    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Open job detail" })).toHaveAttribute(
        "href",
        "/jobs/88",
      );
    });
  });
});
