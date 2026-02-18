import { describe, expect, it } from "vitest";
import { getRedirectForRoute } from "@/lib/auth/guards";

describe("routing guard integration", () => {
  it("routes to onboarding when authenticated and verified but not store-connected", () => {
    const redirect = getRedirectForRoute("/dashboard", {
      A: true,
      V: true,
      S: false,
    });
    expect(redirect).toContain("/onboarding");
  });

  it("does not enforce store requirement on settings route", () => {
    const redirect = getRedirectForRoute("/settings", {
      A: true,
      V: true,
      S: false,
    });
    expect(redirect).toBeNull();
  });
});
