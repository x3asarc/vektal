import { describe, expect, it } from "vitest";
import { createTransportLadder } from "@/features/jobs/observer/transport-ladder";

describe("transport ladder", () => {
  it("falls back from SSE to polling after inactivity threshold", () => {
    const ladder = createTransportLadder({ inactivityThresholdMs: 1000 });
    ladder.markSseEvent(100);
    const next = ladder.checkInactivity(1200);
    expect(next.mode).toBe("polling");
  });

  it("enters degraded mode only when polling also fails", () => {
    const ladder = createTransportLadder({ inactivityThresholdMs: 1000 });
    ladder.markSseEvent(100);
    ladder.checkInactivity(1200);
    expect(ladder.getSnapshot().mode).toBe("polling");

    ladder.markPollingFailure("network_down");
    expect(ladder.getSnapshot().mode).toBe("degraded");
    expect(ladder.getSnapshot().degradationReason).toBe("network_down");
  });
});
