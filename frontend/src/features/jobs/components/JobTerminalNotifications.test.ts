import { describe, expect, it } from "vitest";
import {
  JobTerminalEvent,
  selectVisibleTerminalEvents,
} from "@/features/jobs/components/JobTerminalNotifications";

function event(
  key: string,
  status: JobTerminalEvent["status"],
  occurredAt: number,
): JobTerminalEvent {
  return {
    key,
    jobId: 1,
    status,
    message: `${status} message`,
    occurredAt,
  };
}

describe("job terminal notification policy", () => {
  it("keeps error events sticky while expiring success/cancelled", () => {
    const now = 100_000;
    const events: JobTerminalEvent[] = [
      event("success-old", "success", now - 13_000),
      event("cancel-old", "cancelled", now - 6_000),
      event("error-old", "error", now - 60_000),
    ];

    const result = selectVisibleTerminalEvents(events, now);
    expect(result.visible.map((item) => item.key)).toEqual(["error-old"]);
  });

  it("collapses bursty terminal streams", () => {
    const now = 200_000;
    const events: JobTerminalEvent[] = [
      event("e1", "success", now - 1000),
      event("e2", "cancelled", now - 2000),
      event("e3", "error", now - 3000),
    ];

    const result = selectVisibleTerminalEvents(events, now);
    expect(result.collapsed).toBe(true);
    expect(result.collapsedCount).toBe(3);
  });
});
