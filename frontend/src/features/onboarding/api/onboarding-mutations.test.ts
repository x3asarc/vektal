import { describe, expect, it } from "vitest";
import {
  buildShopifyOauthPath,
  isAckFirstOnlyEndpoint,
} from "@/features/onboarding/api/onboarding-mutations";

describe("onboarding mutations", () => {
  it("marks critical endpoints as ack-first only", () => {
    expect(isAckFirstOnlyEndpoint("/api/v1/jobs")).toBe(true);
    expect(isAckFirstOnlyEndpoint("/api/v1/billing/upgrade")).toBe(true);
    expect(isAckFirstOnlyEndpoint("/api/v1/oauth/shopify")).toBe(true);
    expect(isAckFirstOnlyEndpoint("/api/v1/auth/login")).toBe(true);
  });

  it("does not force ack-first policy for non-critical endpoint", () => {
    expect(isAckFirstOnlyEndpoint("/api/v1/products")).toBe(false);
  });

  it("builds oauth path with shop query parameter", () => {
    expect(buildShopifyOauthPath("https://my-store.myshopify.com/admin")).toBe(
      "/api/v1/oauth/shopify?shop=my-store.myshopify.com",
    );
  });
});
