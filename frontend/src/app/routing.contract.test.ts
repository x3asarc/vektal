import { describe, expect, it } from "vitest";
import { getRedirectForRoute } from "@/lib/auth/guards";

describe("routing contract", () => {
  it("exempts auth routes from global guard waterfall", () => {
    expect(getRedirectForRoute("/auth/login", { A: false, V: false, S: false })).toBeNull();
    expect(getRedirectForRoute("/auth/verify", { A: true, V: false, S: false })).toBeNull();
  });

  it("keeps onboarding exempt from S-check only", () => {
    expect(getRedirectForRoute("/onboarding", { A: true, V: true, S: false })).toBeNull();
    expect(getRedirectForRoute("/onboarding", { A: false, V: true, S: false })).toContain(
      "/auth/login",
    );
  });
});
