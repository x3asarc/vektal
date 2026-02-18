import { describe, expect, it } from "vitest";
import { getChatMode } from "@/shell/components/ChatSurface";
import { sortNotifications } from "@/shell/components/NotificationStack";
import { getSidebarMode } from "@/shell/components/Sidebar";

describe("responsive layout contracts", () => {
  it("applies sidebar breakpoints for sm/md/lg", () => {
    expect(getSidebarMode(500)).toBe("off-canvas");
    expect(getSidebarMode(800)).toBe("non-persistent");
    expect(getSidebarMode(1200)).toBe("persistent");
  });

  it("keeps chat overlay on small/medium and docked on large", () => {
    expect(getChatMode(700)).toBe("overlay");
    expect(getChatMode(1200)).toBe("docked");
  });

  it("sorts notifications by global -> page -> inline -> toast priority", () => {
    const sorted = sortNotifications([
      { level: "toast", message: "toast" },
      { level: "global-blocking", message: "global" },
      { level: "inline", message: "inline" },
    ]);

    expect(sorted.map((item) => item.level)).toEqual([
      "global-blocking",
      "inline",
      "toast",
    ]);
  });
});
