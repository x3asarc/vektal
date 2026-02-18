import { SearchWorkspace } from "@/features/search/components/SearchWorkspace";

export const SEARCH_PAGE_SECTIONS = [
  "search-controls",
  "selection-scope-banner",
  "search-result-grid",
] as const;

export default function SearchPage() {
  return (
    <div data-section={SEARCH_PAGE_SECTIONS[0]}>
      <SearchWorkspace />
    </div>
  );
}
