import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useJobRehydrate } from "@/features/jobs/hooks/useJobRehydrate";

const apiRequestMock = vi.fn<(...args: unknown[]) => Promise<unknown>>();

vi.mock("@/lib/api/client", () => ({
  apiRequest: (...args: unknown[]) => apiRequestMock(...args),
}));

describe("useJobRehydrate", () => {
  beforeEach(() => {
    apiRequestMock.mockReset();
  });

  it("rehydrates active jobs on mount", async () => {
    apiRequestMock.mockResolvedValue({
      jobs: [
        { id: 1, status: "running", job_name: "active" },
        { id: 2, status: "completed", job_name: "done" },
      ],
      total: 2,
    });

    const { result } = renderHook(() => useJobRehydrate());

    await waitFor(() => {
      expect(result.current.rehydrateCount).toBeGreaterThan(0);
    });

    expect(result.current.activeJobs).toHaveLength(1);
    expect(result.current.activeJobs[0]?.id).toBe(1);
  });

  it("rehydrates on focus and online events", async () => {
    apiRequestMock.mockResolvedValue({ jobs: [], total: 0 });

    renderHook(() => useJobRehydrate());

    await waitFor(() => {
      expect(apiRequestMock).toHaveBeenCalledTimes(1);
    });

    act(() => {
      window.dispatchEvent(new Event("focus"));
      window.dispatchEvent(new Event("online"));
    });

    await waitFor(() => {
      expect(apiRequestMock.mock.calls.length).toBeGreaterThanOrEqual(3);
    });
  });
});
