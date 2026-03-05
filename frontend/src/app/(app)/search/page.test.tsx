import { describe, expect, it } from "vitest";
import { SEARCH_PAGE_SECTIONS } from "@/app/(app)/search/sections";
import { SEARCH_COLUMNS } from "@/features/search/components/SearchResultGrid";
import {
  createSelectionFreeze,
  preserveSelectionAcrossFilterChange,
} from "@/features/search/hooks/useSearchWorkspace";

describe("search page contract", () => {
  it("exposes required precision workspace sections", () => {
    expect(SEARCH_PAGE_SECTIONS).toContain("search-controls");
    expect(SEARCH_PAGE_SECTIONS).toContain("selection-scope-banner");
    expect(SEARCH_PAGE_SECTIONS).toContain("search-result-grid");
  });

  it("keeps selection stable when filters change", () => {
    const selected = preserveSelectionAcrossFilterChange([9, 2, 2, 5]);
    expect(selected).toEqual([2, 5, 9]);
  });

  it("builds deterministic selection freeze payload", () => {
    const first = createSelectionFreeze({
      scopeMode: "explicit",
      totalMatching: 18,
      selectedIds: [3, 1, 3],
    });
    const second = createSelectionFreeze({
      scopeMode: "explicit",
      totalMatching: 18,
      selectedIds: [1, 3],
    });
    expect(first.selectionToken).toBe(second.selectionToken);
    expect(first.selectedIds).toEqual([1, 3]);
  });

  it("marks protected columns as non-editable metadata", () => {
    const protectedKeys = SEARCH_COLUMNS.filter((column) => column.protected).map((column) => column.key);
    expect(protectedKeys).toContain("id");
    expect(protectedKeys).toContain("shopify_product_id");
  });
});
