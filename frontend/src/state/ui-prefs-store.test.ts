import { beforeEach, describe, expect, it } from "vitest";
import {
  getUiPrefsStorageKey,
  resolveDeviceBucket,
  useUiPrefsStore,
} from "@/state/ui-prefs-store";

function setViewport(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
}

describe("ui prefs store", () => {
  beforeEach(() => {
    window.localStorage.clear();
    setViewport(1280);
    useUiPrefsStore.getState().hydrate(1280);
    useUiPrefsStore.getState().resetWorkspace();
  });

  it("resolves device bucket from viewport", () => {
    expect(resolveDeviceBucket(500)).toBe("sm");
    expect(resolveDeviceBucket(900)).toBe("md");
    expect(resolveDeviceBucket(1200)).toBe("lg");
  });

  it("persists sidebar preference per device bucket", () => {
    setViewport(1280);
    useUiPrefsStore.getState().hydrate(1280);
    useUiPrefsStore.getState().setSidebarCollapsed(true);

    const raw = window.localStorage.getItem(getUiPrefsStorageKey("lg"));
    expect(raw).not.toBeNull();
    expect(raw).toContain('"sidebarCollapsed":true');
  });

  it("keeps device-specific values isolated", () => {
    useUiPrefsStore.getState().hydrate(1280);
    useUiPrefsStore.getState().setSidebarCollapsed(true);

    useUiPrefsStore.getState().hydrate(500);
    expect(useUiPrefsStore.getState().sidebarCollapsed).toBe(false);
  });
});
