import { describe, expect, it } from "vitest";
import {
  getRedirectForRoute,
  resolveSafeRedirect,
  requiresStore,
  sanitizeReturnTo,
} from "@/lib/auth/guards";

describe("guards", () => {
  it("marks expected routes as store-required", () => {
    expect(requiresStore("/dashboard")).toBe(true);
    expect(requiresStore("/jobs/abc")).toBe(true);
    expect(requiresStore("/settings")).toBe(false);
  });

  it("applies deterministic A/V/S precedence", () => {
    expect(getRedirectForRoute("/dashboard", { A: false, V: false, S: false })).toContain(
      "/auth/login",
    );
    expect(getRedirectForRoute("/dashboard", { A: true, V: false, S: false })).toContain(
      "/auth/verify",
    );
    expect(getRedirectForRoute("/dashboard", { A: true, V: true, S: false })).toContain(
      "/onboarding",
    );
    expect(getRedirectForRoute("/dashboard", { A: true, V: true, S: true })).toBeNull();
  });

  it("allows auth routes to pass through", () => {
    expect(getRedirectForRoute("/auth/login", { A: false, V: false, S: false })).toBeNull();
    expect(getRedirectForRoute("/auth/verify", { A: true, V: false, S: false })).toBeNull();
  });

  it("sanitizes unsafe returnTo values", () => {
    expect(sanitizeReturnTo("https://evil.com")).toBe("/dashboard");
    expect(sanitizeReturnTo("//evil.com")).toBe("/dashboard");
    expect(sanitizeReturnTo("/jobs/1")).toBe("/jobs/1");
  });

  it("avoids redirect loops by falling back", () => {
    expect(resolveSafeRedirect("/dashboard", "/dashboard", "/onboarding")).toBe(
      "/onboarding",
    );
  });
});
