import { describe, expect, it } from "vitest";
import { CHAT_WORKSPACE_SECTIONS } from "@/app/(app)/chat/page";

describe("chat page contract", () => {
  it("declares required workspace sections", () => {
    expect(CHAT_WORKSPACE_SECTIONS).toContain("session-timeline");
    expect(CHAT_WORKSPACE_SECTIONS).toContain("composer");
    expect(CHAT_WORKSPACE_SECTIONS).toContain("action-controls");
    expect(CHAT_WORKSPACE_SECTIONS).toContain("bulk-panel");
  });
});
