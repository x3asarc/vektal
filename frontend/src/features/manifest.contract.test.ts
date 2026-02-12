import { describe, expect, it } from "vitest";
import { FEATURE_MANIFEST } from "@/features/manifest";

describe("feature manifest contract", () => {
  it("defines static ownership entries with required state and render entry", () => {
    expect(FEATURE_MANIFEST.length).toBeGreaterThan(0);
    for (const feature of FEATURE_MANIFEST) {
      expect(feature.id.length).toBeGreaterThan(0);
      expect(feature.routePrefix.startsWith("/")).toBe(true);
      expect(feature.requiredState).toMatch(/^A(\+V)?(\+S)?$/);
      expect(feature.renderEntry).toContain("/");
    }
  });

  it("keeps widget contracts static and explicit", () => {
    const jobs = FEATURE_MANIFEST.find((item) => item.id === "jobs");
    expect(jobs?.widgets?.[0]?.id).toBe("jobs-health-summary");
    expect(jobs?.widgets?.[0]?.requiredState).toBe("A+V+S");
  });
});
