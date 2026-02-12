import { beforeEach, describe, expect, it } from "vitest";
import {
  getDraftStorageKey,
  ttlMs,
  useDraftsStore,
} from "@/state/drafts-store";

describe("drafts store", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    useDraftsStore.getState().clearAllDrafts();
  });

  it("persists non-sensitive drafts in session storage", () => {
    const now = Date.now();
    useDraftsStore.getState().setDraft(
      "onboarding.shop-domain",
      { shop: "test-store.myshopify.com" },
      { now },
    );

    const raw = window.sessionStorage.getItem(
      getDraftStorageKey("onboarding.shop-domain"),
    );
    expect(raw).not.toBeNull();

    const value = useDraftsStore.getState().getDraft<{ shop: string }>(
      "onboarding.shop-domain",
    );
    expect(value?.shop).toBe("test-store.myshopify.com");
  });

  it("drops expired drafts on hydrate", () => {
    const now = Date.now();
    useDraftsStore.getState().setDraft("jobs.filters", { status: "running" }, { now });

    useDraftsStore.getState().hydrate(now + ttlMs + 1);
    const value = useDraftsStore.getState().getDraft<{ status: string }>("jobs.filters");
    expect(value).toBeNull();
  });

  it("never persists sensitive draft payloads", () => {
    useDraftsStore.getState().setDraft(
      "auth.secret",
      { token: "super-secret" },
      { sensitive: true },
    );

    const raw = window.sessionStorage.getItem(getDraftStorageKey("auth.secret"));
    expect(raw).toBeNull();
    expect(useDraftsStore.getState().getDraft("auth.secret")).toBeNull();
  });
});
