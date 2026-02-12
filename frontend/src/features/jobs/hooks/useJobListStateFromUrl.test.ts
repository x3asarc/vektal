import { describe, expect, it } from "vitest";
import {
  buildJobListQuery,
  parseJobListState,
  resetWorkspaceQuery,
} from "@/features/jobs/hooks/useJobListStateFromUrl";

describe("useJobListStateFromUrl helpers", () => {
  it("parses URL params into list state", () => {
    const params = new URLSearchParams("status=running&q=import&page=2");
    expect(parseJobListState(params)).toEqual({
      status: "running",
      search: "import",
      page: 2,
    });
  });

  it("normalizes invalid pages to 1", () => {
    const params = new URLSearchParams("page=-5");
    expect(parseJobListState(params).page).toBe(1);
  });

  it("builds compact query and supports reset workspace action", () => {
    const query = buildJobListQuery({
      status: "failed",
      search: "sku-123",
      page: 1,
    });
    expect(query).toBe("status=failed&q=sku-123");
    expect(resetWorkspaceQuery()).toBe("");
  });
});
