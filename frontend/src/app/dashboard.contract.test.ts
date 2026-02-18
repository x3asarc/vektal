import { describe, expect, it } from "vitest";
import { DASHBOARD_SECTIONS } from "@/app/(app)/dashboard/page";

describe("dashboard contract", () => {
  it("exposes required actionable jobs-health sections", () => {
    expect(DASHBOARD_SECTIONS).toContain("global-health-summary");
    expect(DASHBOARD_SECTIONS).toContain("needs-attention");
    expect(DASHBOARD_SECTIONS).toContain("in-progress");
    expect(DASHBOARD_SECTIONS).toContain("fast-recovery-actions");
  });
});
