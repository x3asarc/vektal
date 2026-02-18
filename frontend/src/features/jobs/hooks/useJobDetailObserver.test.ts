import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useJobDetailObserver } from "@/features/jobs/hooks/useJobDetailObserver";

const apiRequestMock = vi.fn<(...args: unknown[]) => Promise<unknown>>();

vi.mock("@/lib/api/client", () => ({
  apiRequest: (...args: unknown[]) => apiRequestMock(...args),
}));

type Listener = (event: MessageEvent) => void;

class MockEventSource {
  static instances: MockEventSource[] = [];

  onmessage: Listener | null = null;
  onerror: ((event: Event) => void) | null = null;
  listeners = new Map<string, Listener>();

  constructor(_url: string, _init?: EventSourceInit) {
    MockEventSource.instances.push(this);
  }

  addEventListener(name: string, listener: EventListener) {
    this.listeners.set(name, listener as Listener);
  }

  close() {
    return;
  }

  emitNamed(name: string, data: unknown) {
    const listener = this.listeners.get(name);
    if (listener) {
      listener({ data: JSON.stringify(data) } as MessageEvent);
    }
  }

  emitError() {
    this.onerror?.(new Event("error"));
  }
}

describe("useJobDetailObserver", () => {
  beforeEach(() => {
    apiRequestMock.mockReset();
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
  });

  it("consumes named SSE events job_{id}", async () => {
    const { result } = renderHook(() => useJobDetailObserver("5"));
    const source = MockEventSource.instances[0];
    expect(source).toBeTruthy();

    act(() => {
      source.emitNamed("job_5", {
        job_id: 5,
        status: "running",
        current_step_label: "Scraping Web",
        percent_complete: 47.5,
      });
    });

    await waitFor(() => {
      expect(result.current.job?.id).toBe(5);
    });
    expect(result.current.job?.current_step_label).toBe("Scraping Web");
    expect(result.current.mode).toBe("sse");
    expect(result.current.degraded).toBe(false);
  });

  it("falls back to polling when SSE errors before first event", async () => {
    apiRequestMock.mockResolvedValue({
      job: { id: 5, status: "running", current_step_label: "Queued" },
    });

    const { result } = renderHook(() => useJobDetailObserver("5"));
    const source = MockEventSource.instances[0];

    act(() => {
      source.emitError();
    });

    await waitFor(() => {
      expect(apiRequestMock).toHaveBeenCalledWith("/api/v1/jobs/5");
    });
    await waitFor(() => {
      expect(result.current.mode).toBe("polling");
    });
  });
});
