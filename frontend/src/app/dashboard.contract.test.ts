import { describe, expect, it } from "vitest";
import { DASHBOARD_SECTIONS } from "@/app/(app)/dashboard/sections";

describe("dashboard contract", () => {
  it("exposes required actionable jobs-health sections", () => {
    expect(DASHBOARD_SECTIONS).toContain("session-status");
    expect(DASHBOARD_SECTIONS).toContain("telemetry-grid");
    expect(DASHBOARD_SECTIONS).toContain("next-operators");
  });
});
